"""CLI entry for the daily wallet scrape.

Builds the live Helius transport from ``HELIUS_API_KEY``, discovers candidate
wallets from high-activity programs, runs the scrape, and writes a dated CSV plus
a small markdown summary. Designed for a scheduled GitHub Actions run at midnight
US/Eastern (the workflow triggers at both 04:00 and 05:00 UTC to cover DST and
this runner only proceeds during the true Eastern-midnight hour, unless forced).
"""

from __future__ import annotations

import csv
import os
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from wis.jobs.daily_scrape import DEFAULT_PROGRAMS, ScrapeConfig, ScrapeResult, scrape


def is_eastern_midnight(now: datetime | None = None) -> bool:
    et = (now or datetime.now(tz=ZoneInfo("America/New_York"))).astimezone(ZoneInfo("America/New_York"))
    return et.hour == 0


def build_transport():
    key = os.environ.get("HELIUS_API_KEY")
    if not key:
        raise SystemExit("HELIUS_API_KEY is not set (add it as a repository secret).")
    from wis.sources.helius_live import HeliusLiveTransport

    return HeliusLiveTransport(key)


def discover(transport, programs=DEFAULT_PROGRAMS, *, pages_per_program: int = 30) -> Iterator[str]:
    """Yield distinct candidate wallets (fee payers) from high-activity programs,
    interleaved across programs for diversity."""
    from wis.research.reality_lab.universes import fee_payers_from_enhanced

    pools = []
    for prog in programs:
        try:
            pools.append(fee_payers_from_enhanced(transport.transactions(prog, limit=100, max_pages=pages_per_program)))
        except Exception:
            pools.append([])
    seen: set[str] = set()
    i = 0
    while any(i < len(p) for p in pools):
        for p in pools:
            if i < len(p) and p[i] not in seen:
                seen.add(p[i])
                yield p[i]
        i += 1


def write_outputs(result: ScrapeResult, out_dir: str | Path, day: str) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / f"wallets-{day}.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["wallet", "closed_trades", "trades_per_day", "active_days", "confidence",
                    "win_rate", "median_multiple", "sharpe", "alpha_score",
                    "primary_quote", "primary_pnl", "primary_roi"])
        for r in result.qualifying:
            w.writerow([r.wallet, r.closed_trades, f"{r.trades_per_day:.2f}", f"{r.active_days:.2f}",
                        f"{r.confidence:.3f}", _n(r.win_rate), _n(r.median_multiple), _n(r.sharpe),
                        _n(r.alpha_score), r.primary_quote or "", _n(r.primary_pnl), _n(r.primary_roi)])
    summary_path = out / f"summary-{day}.md"
    summary_path.write_text(_summary_md(result, day))
    return csv_path, summary_path


def _n(x: float | None) -> str:
    return "" if x is None else f"{x:.6f}"


def _summary_md(result: ScrapeResult, day: str) -> str:
    top = result.qualifying[:25]
    lines = [
        f"# Daily wallet scrape — {day}",
        "",
        f"* Qualifying wallets: **{len(result.qualifying)}** (target 5,000)",
        f"* Candidates discovered: {result.candidates_discovered} · observed: {result.candidates_observed}",
        f"* Elapsed: {result.elapsed_seconds/60:.1f} min · stopped: `{result.stopped_reason}`",
        "",
        "Qualified = active (≥5 closed trades AND ≥5 trades/day) AND strong",
        "(confidence-shrunk alpha ≥ 0.55 AND positive primary-quote ROI). PnL is",
        "per quote asset; every rate shows its denominator. Full list in the CSV.",
        "",
        "| # | wallet | trades | t/day | conf | alpha | quote | ROI% |",
        "|--:|--------|-------:|------:|-----:|------:|:-----:|-----:|",
    ]
    for i, r in enumerate(top, 1):
        short = f"{r.wallet[:4]}…{r.wallet[-4:]}"
        roi = f"{r.primary_roi:.1%}" if r.primary_roi is not None else "—"
        a = f"{r.alpha_score:.3f}" if r.alpha_score is not None else "—"
        lines.append(f"| {i} | `{short}` | {r.closed_trades} | {r.trades_per_day:.1f} | "
                     f"{r.confidence:.2f} | {a} | {r.primary_quote or '—'} | {roi} |")
    return "\n".join(lines)


def _main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="wis.jobs.runner", description="Daily active-trader wallet scrape.")
    p.add_argument("--out-dir", default="ratings/daily")
    p.add_argument("--target", type=int, default=5000)
    p.add_argument("--candidate-budget", type=int, default=60000)
    p.add_argument("--pages-per-wallet", type=int, default=2)
    p.add_argument("--pages-per-program", type=int, default=30)
    p.add_argument("--min-trades-per-day", type=float, default=5.0)
    p.add_argument("--min-alpha", type=float, default=0.55)
    p.add_argument("--force", action="store_true", help="run even if not Eastern midnight")
    args = p.parse_args(argv)

    if not args.force and not is_eastern_midnight():
        print("Not the Eastern-midnight hour; skipping (use --force to override).")
        return 0

    cfg = ScrapeConfig(
        target=args.target,
        candidate_budget=args.candidate_budget,
        pages_per_wallet=args.pages_per_wallet,
        min_trades_per_day=args.min_trades_per_day,
        min_alpha=args.min_alpha,
    )
    transport = build_transport()
    day = datetime.now(tz=ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    result = scrape(transport, discover(transport, pages_per_program=args.pages_per_program), cfg)
    csv_path, summary_path = write_outputs(result, args.out_dir, day)

    # Optional: upsert to a durable rating store if a DSN is configured.
    dsn = os.environ.get("WIS_PG_DSN")
    if dsn:
        print(f"(WIS_PG_DSN set — a Postgres rating store would be upserted here: {len(result.qualifying)} rows)")

    print(f"Qualifying: {len(result.qualifying)}  observed: {result.candidates_observed}  "
          f"stopped: {result.stopped_reason}")
    print(f"Wrote {csv_path} and {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
