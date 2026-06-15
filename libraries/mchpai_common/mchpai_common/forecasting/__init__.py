"""Forecasting — generic time-series & survival toolkit.

Shared forecasting primitives used across feature/prediction engines: simple
exponential smoothing with drift (Holt), and a survival estimate for "how long
until a position should be exited / a token rugs" framed as a hazard.
"""

from __future__ import annotations

import numpy as np


def holt_forecast(series: np.ndarray, alpha: float = 0.5, beta: float = 0.3, horizon: int = 1) -> float:
    """Holt's linear (double exponential) smoothing forecast `horizon` ahead."""
    x = np.asarray(series, dtype=float)
    if x.size == 0:
        return 0.0
    if x.size == 1:
        return float(x[0])
    level = x[0]
    trend = x[1] - x[0]
    for v in x[1:]:
        prev_level = level
        level = alpha * v + (1 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1 - beta) * trend
    return float(level + horizon * trend)


def exponential_hazard_survival(elapsed_seconds: float, half_life_seconds: float) -> float:
    """P(token/position still 'alive' after elapsed time) given a half-life."""
    if half_life_seconds <= 0:
        return 0.0
    lam = np.log(2.0) / half_life_seconds
    return float(np.exp(-lam * max(elapsed_seconds, 0.0)))


def expected_value(p_up: float, up_bps: float, down_bps: float, cost_bps: float = 0.0) -> float:
    """EV of a binary up/down outcome, net of costs, in bps."""
    return float(p_up * up_bps - (1.0 - p_up) * down_bps - cost_bps)
