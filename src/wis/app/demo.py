"""A self-contained tour of the observatory.

Run with ``python -m wis.app.demo``. It seeds a small synthetic world entirely
in memory — no infrastructure required — and prints the intelligence the system
derives: wallet DNA, scores, the alpha leaderboard, communities, and a wallet's
evolution as a movie. This is the fastest way to *see* what the platform does.
"""

from __future__ import annotations

from wis.app.observatory import Observatory
from wis.domain.events import (
    TokenPriceObserved,
    WalletBoughtToken,
    WalletCreated,
    WalletFunded,
    WalletSoldToken,
)
from wis.domain.identifiers import TokenMint, WalletAddress
from wis.domain.money import Amount
from wis.domain.time import DAY, Nanos
from wis.research import sequence_lab, wallet_alpha_lab

LAMPORTS, TOKDEC = 9, 6


def sol(x: float) -> Amount:
    return Amount(raw=int(round(x * 10**LAMPORTS)), decimals=LAMPORTS)


def tok(x: float) -> Amount:
    return Amount(raw=int(round(x * 10**TOKDEC)), decimals=TOKDEC)


def build() -> Observatory:
    obs = Observatory()
    clock = {"t": DAY}

    def at() -> Nanos:
        return Nanos(clock["t"])

    def adv(ns: int = DAY) -> None:
        clock["t"] += ns

    def created(w: str, funder: str | None = None) -> None:
        obs.ingest(
            WalletCreated(occurred_at=at(), wallet=WalletAddress(w),
                          funded_by=WalletAddress(funder) if funder else None),
            ingestion_time=at(),
        )
        adv()

    def funded(src: str, dst: str, amt: float) -> None:
        obs.ingest(WalletFunded(occurred_at=at(), source=WalletAddress(src),
                                target=WalletAddress(dst), amount=sol(amt)), ingestion_time=at())
        adv()

    def price(t: str, p: float) -> None:
        obs.ingest(TokenPriceObserved(occurred_at=at(), token=TokenMint(t),
                                      price_quote_per_base=sol(p)), ingestion_time=at())
        adv(0)

    def buy(w: str, t: str, base: float, quote: float) -> None:
        obs.ingest(WalletBoughtToken(occurred_at=at(), wallet=WalletAddress(w),
                                     token=TokenMint(t), base=tok(base), quote=sol(quote)),
                   ingestion_time=at())
        adv(3 * 3600 * 10**9)  # 3 hours

    def sell(w: str, t: str, base: float, quote: float) -> None:
        obs.ingest(WalletSoldToken(occurred_at=at(), wallet=WalletAddress(w),
                                   token=TokenMint(t), base=tok(base), quote=sol(quote)),
                   ingestion_time=at())
        adv()

    # A funder seeds a coordinated cohort; they co-buy a winning token.
    created("funder")
    for w in ["scout", "follower_a", "follower_b"]:
        created(w, funder="funder")
        funded("funder", w, 10.0)

    # 'scout' is a skilled, patient, early entrant across many tokens.
    for i in range(12):
        t = f"GEM{i}"
        price(t, 1.0)
        buy("scout", t, 1000, 1.0)
        price(t, 4.0)
        sell("scout", t, 1000, 4.0)

    # Followers pile into the same tokens, later and worse.
    for i in range(8):
        t = f"GEM{i}"
        price(t, 3.0)
        buy("follower_a", t, 100, 3.0)
        buy("follower_b", t, 100, 3.0)
        price(t, 2.0)
        sell("follower_a", t, 100, 2.0)
        sell("follower_b", t, 100, 2.0)

    return obs


def main() -> None:
    obs = build()
    print("=" * 72)
    print(" MCHPAI Advanced Wallet Intelligence System — observatory tour")
    print("=" * 72)
    print(f"\nEvents in log: {int(obs.store.head)}   Wallets: {len(obs.list_wallets())}\n")

    print("── Alpha leaderboard (truth-weighted, confidence-filtered) ──")
    for r in wallet_alpha_lab.leaderboard(obs, min_confidence=0.1):
        a = f"{r.alpha_score:.3f}" if r.alpha_score is not None else "  n/a"
        print(f"  {r.address.value:<14} alpha={a}  conf={r.confidence:.2f}  trades={r.sample_size}")

    print("\n── Wallet DNA: scout ──")
    report = obs.wallet_report(WalletAddress("scout"))
    assert report is not None
    print(f"  {report.frame.dna.summary()}")
    p = report.frame.performance
    sharpe = f"{p.sharpe_ratio:.2f}" if p.sharpe_ratio is not None else "n/a (no variance)"
    print(f"  lifetime_roi={p.lifetime_roi:.2%}  win_rate={p.win_rate:.0%}  sharpe={sharpe}")

    def fmt(x: float | None) -> str:
        return f"{x:.3f}" if x is not None else "n/a"

    s = report.scores
    print(f"  scores: alpha={fmt(s.wallet_alpha_score)} timing={fmt(s.timing_score)} "
          f"conviction={fmt(s.conviction_score)} ev={fmt(s.expected_value_score)}")

    print("\n── Communities (Louvain) ──")
    for cid, members in obs.clusters().items():
        print(f"  {cid.value}: {[m.value for m in members]}")
    gs = obs.graph_summary()
    print(f"  nodes={gs.node_count} edges={gs.edge_count} "
          f"density={gs.density:.3f} modularity={gs.modularity:.3f}")

    print("\n── scout as a movie (alpha over time) ──")
    for frame in sequence_lab.wallet_timeline(obs, WalletAddress("scout"))[::3]:
        a = f"{frame.alpha_score:.3f}" if frame.alpha_score is not None else "n/a"
        print(f"  seq={int(frame.sequence):>3}  trades={frame.closed_trades:>2}  "
              f"alpha={a}  conf={frame.confidence:.2f}")
    print()


if __name__ == "__main__":
    main()
