"""Wallet ratings: quote-internal ratios pool correctly, absolute PnL stays
per-quote (SOL and USDC never summed), and the store ranks with denominators."""

from __future__ import annotations

from wis.domain.events import WalletBoughtToken, WalletSoldToken
from wis.domain.identifiers import TokenMint, WalletAddress
from wis.domain.money import Amount
from wis.domain.time import DAY, Nanos
from wis.eventsourcing.replay import ReplayEngine
from wis.eventsourcing.store import InMemoryEventStore
from wis.projections.wallet_projector import WalletProjector
from wis.ratings.leaderboard import render_markdown
from wis.ratings.rater import rate_wallet, rate_world
from wis.ratings.store import SqliteRatingStore


def _sol(x: float) -> Amount:
    return Amount(raw=int(round(x * 1e9)), decimals=9)


def _usdc(x: float) -> Amount:
    return Amount(raw=int(round(x * 1e6)), decimals=6)


def _tok(x: float) -> Amount:
    return Amount(raw=int(round(x * 1e6)), decimals=6)


def _world():
    store = InMemoryEventStore()
    t = [DAY]

    def at() -> Nanos:
        t[0] += DAY
        return Nanos(t[0])

    a = WalletAddress("w")
    evs = [
        # SOL win: 1 -> 3
        WalletBoughtToken(occurred_at=at(), wallet=a, token=TokenMint("AAA"), base=_tok(1000), quote=_sol(1)),
        WalletSoldToken(occurred_at=at(), wallet=a, token=TokenMint("AAA"), base=_tok(1000), quote=_sol(3)),
        # SOL loss: 1 -> 0.5
        WalletBoughtToken(occurred_at=at(), wallet=a, token=TokenMint("BBB"), base=_tok(1000), quote=_sol(1)),
        WalletSoldToken(occurred_at=at(), wallet=a, token=TokenMint("BBB"), base=_tok(1000), quote=_sol(0.5)),
        # USDC win: 10 -> 15
        WalletBoughtToken(occurred_at=at(), wallet=a, token=TokenMint("CCC"), base=_tok(100), quote=_usdc(10), quote_mint="USDC"),
        WalletSoldToken(occurred_at=at(), wallet=a, token=TokenMint("CCC"), base=_tok(100), quote=_usdc(15), quote_mint="USDC"),
    ]
    for e in evs:
        store.append(e, ingestion_time=Nanos(int(e.occurred_at) + 1))
    return ReplayEngine(store, WalletProjector()).run()


def test_rating_keeps_pnl_per_quote() -> None:
    world = _world()
    r = rate_wallet(world.wallets[WalletAddress("w")], prices=world.prices)
    assert r.closed_trades == 3
    assert r.win_rate == 2 / 3                       # 2 wins of 3, pooled
    assert r.primary_quote == "SOL"                  # 2 SOL trades vs 1 USDC
    # PnL never summed across currencies:
    assert round(r.pnl_by_quote["SOL"], 6) == 1.5    # +2 and -0.5
    assert round(r.pnl_by_quote["USDC"], 6) == 5.0
    assert round(r.roi_by_quote["SOL"], 6) == 0.75   # 1.5 / 2.0 cost
    assert round(r.roi_by_quote["USDC"], 6) == 0.5   # 5 / 10 cost


def test_store_ranks_with_floors() -> None:
    world = _world()
    store = SqliteRatingStore()
    store.upsert(rate_world(world))
    assert store.count() == 1
    # Floor filters out wallets without enough evidence.
    assert store.top(by="win_rate", min_trades=10) == []
    top = store.top(by="win_rate", min_trades=1)
    assert top and top[0].wallet == "w"
    got = store.get("w")
    assert got is not None and got.win_rate == 2 / 3


def test_leaderboard_renders_with_denominators() -> None:
    world = _world()
    md = render_markdown(rate_world(world))
    assert "trades" in md and "conf" in md
    assert "`w`" in md
