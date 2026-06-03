"""Lifecycle phase detection.

Labels each snapshot in a token's ordered sequence as birth / growth / viral /
distribution / death. This converts a flat time-series into a *phase-annotated
sequence* — exactly what sequence models need to learn transitions (e.g. "growth
→ distribution" as an exit signal).

Heuristics here are deliberate, transparent baselines; a learned phase model can
later replace :func:`classify_phase` without changing the sequence contract.
"""

from __future__ import annotations

from ..schemas.snapshot import LifecyclePhase, TokenSnapshot

# thresholds (tunable; conservative defaults)
_VIRAL_R0 = 1.5
_GROWTH_NETFLOW = 0.0
_DEATH_LIQ_FRAC = 0.15        # liquidity fell below 15% of peak
_DISTRIB_NETFLOW_FRAC = -0.2  # sustained net outflow vs volume


def classify_phase(
    snap: TokenSnapshot,
    *,
    peak_liquidity: float | None = None,
    peak_price: float | None = None,
) -> LifecyclePhase:
    liq = snap.liquidity_sol
    # death: liquidity collapsed relative to its peak
    if peak_liquidity and liq is not None and peak_liquidity > 0:
        if liq <= _DEATH_LIQ_FRAC * peak_liquidity:
            return LifecyclePhase.death

    # birth: very young and little traction yet
    if snap.age_seconds < 60 and snap.txns < 20:
        return LifecyclePhase.birth

    # viral: high reproduction and strong positive flow
    if (snap.r0 or 0) >= _VIRAL_R0 and snap.net_flow_sol > 0:
        return LifecyclePhase.viral

    # distribution: sustained net outflow (smart money exiting)
    vol = snap.volume_sol or 0.0
    if vol > 0 and (snap.net_flow_sol / vol) <= _DISTRIB_NETFLOW_FRAC:
        return LifecyclePhase.distribution

    # growth: positive net flow / rising price
    if snap.net_flow_sol > _GROWTH_NETFLOW:
        return LifecyclePhase.growth

    return LifecyclePhase.distribution


def label_sequence(snaps: list[TokenSnapshot]) -> list[TokenSnapshot]:
    """Annotate an ordered snapshot sequence in place with phases.

    Tracks running peaks so 'death'/'distribution' are judged against the token's
    own history, not absolute thresholds. Returns the same list for chaining.
    """
    peak_liq = 0.0
    peak_px = 0.0
    for s in snaps:
        if s.liquidity_sol:
            peak_liq = max(peak_liq, s.liquidity_sol)
        if s.price_sol:
            peak_px = max(peak_px, s.price_sol)
        s.phase = classify_phase(s, peak_liquidity=peak_liq or None, peak_price=peak_px or None)
    return snaps
