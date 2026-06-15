"""Label computation from a token's snapshot sequence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..schemas.ground_truth import (
    HORIZON_SECONDS,
    HORIZONS,
    MULTIPLES,
    GroundTruth,
    Outcome,
)

# rug heuristics
_RUG_LIQ_FRAC = 0.10        # liquidity collapsed below 10% of peak
_RUG_PRICE_DRAWDOWN = 0.90  # price fell ≥90% from peak
_VIRAL_MULTIPLE = 10.0


@dataclass
class SnapshotPoint:
    """Minimal slice of a snapshot needed for labeling (ordered by age)."""

    age_seconds: float
    price_sol: float | None
    liquidity_sol: float | None = None
    holders: int | None = None


def compute_ground_truth(
    mint: str,
    created_at: datetime,
    points: list[SnapshotPoint],
    *,
    reference_price: float | None = None,
) -> GroundTruth:
    gt = GroundTruth(mint=mint, created_at=created_at)
    pts = [p for p in sorted(points, key=lambda p: p.age_seconds) if p.price_sol]
    if not pts:
        return gt

    ref = reference_price or pts[0].price_sol
    gt.reference_price = ref
    if not ref or ref <= 0:
        return gt

    # achieved[Nx][horizon] and per-horizon max multiple
    achieved = {f"{m}x": {h: False for h in HORIZONS} for m in MULTIPLES}
    max_by_h = {h: 1.0 for h in HORIZONS}
    overall_max, t_to_max = 1.0, None
    peak_liq = max((p.liquidity_sol or 0.0) for p in pts)
    peak_holders = max((p.holders or 0) for p in pts)

    for p in pts:
        mult = p.price_sol / ref
        if mult > overall_max:
            overall_max, t_to_max = mult, p.age_seconds
        for h in HORIZONS:
            if p.age_seconds <= HORIZON_SECONDS[h]:
                max_by_h[h] = max(max_by_h[h], mult)
                for m in MULTIPLES:
                    if mult >= m:
                        achieved[f"{m}x"][h] = True

    gt.achieved = achieved
    gt.max_multiple = overall_max
    gt.time_to_max_seconds = t_to_max
    gt.max_multiple_by_horizon = max_by_h

    # rug detection: liquidity collapse or catastrophic drawdown from peak
    peak_price = max(p.price_sol for p in pts)
    rugged_at = None
    for p in pts:
        liq_gone = peak_liq > 0 and (p.liquidity_sol or 0.0) <= _RUG_LIQ_FRAC * peak_liq
        crashed = peak_price > 0 and p.price_sol <= (1 - _RUG_PRICE_DRAWDOWN) * peak_price
        if liq_gone or (crashed and p.age_seconds > 60):
            rugged_at = created_at + timedelta(seconds=p.age_seconds)
            break

    last_age = pts[-1].age_seconds
    if rugged_at is not None:
        gt.outcome = Outcome.rugged
        gt.rugged_at = rugged_at
        gt.survival_seconds = (rugged_at - created_at).total_seconds()
    elif overall_max >= _VIRAL_MULTIPLE and last_age >= HORIZON_SECONDS["24h"]:
        gt.outcome = Outcome.viral
        gt.survival_seconds = last_age
    elif last_age >= HORIZON_SECONDS["7d"]:
        gt.outcome = Outcome.survived
        gt.survival_seconds = last_age
    else:
        gt.outcome = Outcome.pending
        gt.survival_seconds = last_age

    if peak_holders > 0:
        gt.holder_retention = (pts[-1].holders or 0) / peak_holders

    gt.labeled_at = datetime.now(created_at.tzinfo)
    gt.is_final = last_age >= HORIZON_SECONDS["7d"] or rugged_at is not None
    return gt
