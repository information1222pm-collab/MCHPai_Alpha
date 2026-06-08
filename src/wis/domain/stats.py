"""Deterministic, dependency-free statistics.

The intelligence core must import with zero third-party packages, so we cannot
lean on numpy here. These helpers are pure and stable: same input, same output,
on any machine, forever. numpy/scipy are reserved for the research layer where
approximation and speed matter more than the core's reproducibility contract.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def median(xs: Sequence[float]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def pstdev(xs: Sequence[float]) -> float:
    """Population standard deviation."""
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def downside_deviation(xs: Sequence[float], target: float = 0.0) -> float:
    """Root-mean-square of below-target deviations — the denominator of Sortino."""
    below = [(x - target) ** 2 for x in xs if x < target]
    if not below:
        return 0.0
    return math.sqrt(sum(below) / len(xs))


def percentile_rank(value: float, population: Sequence[float]) -> float | None:
    """Fraction of ``population`` strictly below ``value`` (0..1). ``None`` if the
    population is empty. The basis of entry/exit timing percentiles."""
    if not population:
        return None
    below = sum(1 for p in population if p < value)
    return below / len(population)


def herfindahl(weights: Sequence[float]) -> float:
    """Herfindahl–Hirschman concentration index (0 diffuse .. 1 concentrated)."""
    total = sum(weights)
    if total <= 0:
        return 0.0
    return sum((w / total) ** 2 for w in weights)


def max_drawdown(equity_curve: Sequence[float]) -> float:
    """Largest peak-to-trough drop on a cumulative curve. Returned as a
    non-negative magnitude in the curve's own units."""
    peak = -math.inf
    worst = 0.0
    for v in equity_curve:
        peak = max(peak, v)
        worst = max(worst, peak - v)
    return worst


def max_consecutive(flags: Sequence[bool]) -> int:
    """Longest run of ``True`` — used for max consecutive losing trades."""
    best = run = 0
    for f in flags:
        run = run + 1 if f else 0
        best = max(best, run)
    return best
