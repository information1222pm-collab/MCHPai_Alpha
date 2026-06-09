"""Render wallet ratings as a leaderboard — with denominators, always.

A leaderboard is dangerous: it invites trust. So every row shows the evidence
behind it (closed trades, confidence) and PnL is shown in its own quote. Wallets
below a trade/confidence floor are not ranked — a top spot earned on 2 lucky
trades is a lie the Statistics doctrine forbids.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from io import StringIO

from wis.ratings.model import WalletRating


def _fmt(x: float | None, pct: bool = False) -> str:
    if x is None:
        return "—"
    return f"{x:.1%}" if pct else f"{x:.3f}"


def render_markdown(ratings: Sequence[WalletRating], *, title: str = "Wallet leaderboard") -> str:
    lines = [
        f"# {title}",
        "",
        f"{len(ratings)} wallets, ranked. Every rate shows its denominator (closed",
        "trades) and confidence. PnL/ROI are per the wallet's primary quote asset —",
        "never summed across currencies. Ratings are observation, not advice.",
        "",
        "| # | wallet | trades | conf | win% | alpha | quote | PnL (quote) | ROI% |",
        "|--:|--------|-------:|-----:|-----:|------:|:-----:|------------:|-----:|",
    ]
    for i, r in enumerate(ratings, 1):
        short = r.wallet if len(r.wallet) <= 12 else f"{r.wallet[:4]}…{r.wallet[-4:]}"
        pnl = f"{r.primary_pnl:.3f}" if r.primary_pnl is not None else "—"
        lines.append(
            f"| {i} | `{short}` | {r.closed_trades} | {r.confidence:.2f} | "
            f"{_fmt(r.win_rate, pct=True)} | {_fmt(r.alpha_score)} | "
            f"{r.primary_quote or '—'} | {pnl} | {_fmt(r.primary_roi, pct=True)} |"
        )
    return "\n".join(lines)


def render_csv(ratings: Sequence[WalletRating]) -> str:
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["wallet", "closed_trades", "confidence", "win_rate", "median_multiple",
                "sharpe", "alpha_score", "ev_score", "conviction_score", "risk_score",
                "timing_score", "primary_quote", "primary_pnl", "primary_roi"])
    for r in ratings:
        w.writerow([r.wallet, r.closed_trades, f"{r.confidence:.4f}",
                    _num(r.win_rate), _num(r.median_multiple), _num(r.sharpe),
                    _num(r.alpha_score), _num(r.expected_value_score), _num(r.conviction_score),
                    _num(r.risk_score), _num(r.timing_score), r.primary_quote or "",
                    _num(r.primary_pnl), _num(r.primary_roi)])
    return buf.getvalue()


def _num(x: float | None) -> str:
    return "" if x is None else f"{x:.6f}"
