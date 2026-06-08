"""Reproducibility statistics — turning point estimates into estimates *with error*.

One session gives a single proportion; it does not tell us whether that
proportion is stable. Phase 6 runs the *same* universe across multiple fresh
sessions and asks: does ``P(BUG-001 | universe)`` reproduce? This module provides
the honest statistics for that question, dependency-free:

* :func:`wilson_interval` — a binomial confidence interval for a single
  proportion that stays sane at small ``n`` (where the naive Wald interval lies).
* :func:`summarize` — across-trial mean, variance and a t-interval, capturing the
  variability introduced by *which wallets we happened to sample*.

Doctrine (see ``docs/STATISTICS.md``): every rate reveals its denominator; a rate
over ``n < 100`` is low-confidence; unknown beats false precision.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

LOW_CONFIDENCE_N = 100

# Two-sided 95% Student-t critical values by degrees of freedom (n-1). Small
# table so we need no scipy; falls back to the normal approximation (1.96).
_T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447,
        7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 15: 2.131, 20: 2.086, 30: 2.042}


def _t_critical(dof: int) -> float:
    if dof <= 0:
        return float("nan")
    if dof in _T95:
        return _T95[dof]
    # nearest smaller tabulated dof, else normal approx
    candidates = [d for d in _T95 if d <= dof]
    return _T95[max(candidates)] if candidates else 1.96


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion. Honest at small n."""
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


@dataclass(frozen=True, slots=True)
class Summary:
    n_trials: int
    mean: float
    variance: float
    std: float
    sem: float
    ci_lo: float
    ci_hi: float
    total_denominator: int  # pooled n across trials, for context

    @property
    def low_confidence(self) -> bool:
        return self.total_denominator < LOW_CONFIDENCE_N or self.n_trials < 3

    def as_pct(self) -> str:
        flag = " ⚠" if self.low_confidence else ""
        return f"{self.mean:.1%} ± {(self.ci_hi - self.mean):.1%} (95% CI){flag}"


def summarize(values: Sequence[float], denominators: Sequence[int] = ()) -> Summary:
    """Across-trial mean ± 95% t-interval. ``values`` are per-trial proportions;
    ``denominators`` (optional) are each trial's sample size, pooled for context."""
    k = len(values)
    if k == 0:
        return Summary(0, float("nan"), float("nan"), float("nan"), float("nan"),
                       float("nan"), float("nan"), 0)
    mean = sum(values) / k
    if k == 1:
        return Summary(1, mean, 0.0, 0.0, 0.0, mean, mean, sum(denominators) if denominators else 0)
    variance = sum((v - mean) ** 2 for v in values) / (k - 1)  # sample variance
    std = math.sqrt(variance)
    sem = std / math.sqrt(k)
    half = _t_critical(k - 1) * sem
    return Summary(
        n_trials=k,
        mean=mean,
        variance=variance,
        std=std,
        sem=sem,
        ci_lo=max(0.0, mean - half),
        ci_hi=min(1.0, mean + half),
        total_denominator=sum(denominators) if denominators else 0,
    )
