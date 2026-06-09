"""Compute wallet ratings from observed state.

Reuses the existing intelligence: ``wallet_state(t)`` → metrics + truth-weighted
scores, plus a per-quote PnL pass over the exact ledger. No new modeling — just
the rating surface the scoring engine was always meant to feed.
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction

from wis.domain.wallet.state import WalletState
from wis.projections.wallet_projector import WalletWorld
from wis.ratings.model import WalletRating
from wis.scoring.scores import score_wallet


def _per_quote_pnl(ws: WalletState) -> tuple[dict[str, float], dict[str, float], str | None]:
    pnl: dict[str, Fraction] = defaultdict(Fraction)
    cost: dict[str, Fraction] = defaultdict(Fraction)
    count: dict[str, int] = defaultdict(int)
    for t in ws.ledger.closed:
        pnl[t.quote] += t.pnl
        cost[t.quote] += t.cost
        count[t.quote] += 1
    pnl_by = {q: float(v) for q, v in pnl.items()}
    roi_by = {q: float(pnl[q] / cost[q]) for q in cost if cost[q] > 0}
    primary = max(count, key=count.get) if count else None
    return pnl_by, roi_by, primary


def rate_wallet(ws: WalletState, prices=None) -> WalletRating:
    frame = ws.frame(prices=prices)
    scores = score_wallet(frame)
    p = frame.performance
    pnl_by, roi_by, primary = _per_quote_pnl(ws)
    return WalletRating(
        wallet=ws.address.value,
        closed_trades=frame.sample_size,
        distinct_tokens=frame.conviction.distinct_tokens,
        open_positions=len(ws.open_positions()),
        confidence=scores.confidence,
        win_rate=p.win_rate,
        median_multiple=p.median_multiple,
        average_multiple=p.average_multiple,
        sharpe=p.sharpe_ratio,
        alpha_score=scores.wallet_alpha_score,
        expected_value_score=scores.expected_value_score,
        conviction_score=scores.conviction_score,
        risk_score=scores.risk_score,
        timing_score=scores.timing_score,
        primary_quote=primary,
        pnl_by_quote=pnl_by,
        roi_by_quote=roi_by,
    )


def rate_world(world: WalletWorld) -> list[WalletRating]:
    """Rate every wallet in a projected world. Deterministic order by address."""
    return [
        rate_wallet(world.wallets[addr], prices=world.prices)
        for addr in sorted(world.wallets, key=lambda a: a.value)
    ]
