"""Generic quantitative indicators (online + batch).

Reusable building blocks for feature engineering: EWMA, rolling z-score, rate of
change, imbalance, Gini concentration. All numpy-based and side-effect free.
"""

from __future__ import annotations

import numpy as np


def ewma(values: np.ndarray, halflife: float) -> np.ndarray:
    """Exponentially-weighted moving average with a given half-life."""
    alpha = 1.0 - np.exp(np.log(0.5) / max(halflife, 1e-9))
    out = np.empty_like(values, dtype=float)
    acc = values[0] if len(values) else 0.0
    for i, v in enumerate(values):
        acc = alpha * v + (1 - alpha) * acc
        out[i] = acc
    return out


def zscore(values: np.ndarray) -> float:
    """Z-score of the last value vs. the window."""
    if len(values) < 2:
        return 0.0
    mu, sd = float(np.mean(values[:-1])), float(np.std(values[:-1]))
    return (float(values[-1]) - mu) / sd if sd > 1e-9 else 0.0


def rate_of_change(values: np.ndarray, periods: int = 1) -> float:
    if len(values) <= periods or values[-periods - 1] == 0:
        return 0.0
    return float(values[-1] / values[-periods - 1] - 1.0)


def imbalance(buys: float, sells: float) -> float:
    """Order-flow imbalance in [-1, 1]: +1 all buys, -1 all sells."""
    total = buys + sells
    return (buys - sells) / total if total > 0 else 0.0


def gini(values: np.ndarray) -> float:
    """Gini concentration in [0,1] — used for holder concentration features."""
    v = np.sort(np.asarray(values, dtype=float))
    n = len(v)
    if n == 0 or v.sum() == 0:
        return 0.0
    cum = np.cumsum(v)
    return float((n + 1 - 2 * np.sum(cum) / cum[-1]) / n)
