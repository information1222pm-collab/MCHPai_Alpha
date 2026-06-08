"""Squashing and shrinkage helpers for truth-oriented scoring.

Scores live in [0, 1] and answer "how strongly does the evidence support this
quality?" — not "how profitable was this wallet?". Two ideas matter here:

* **Bounded monotone transforms** map unbounded metrics onto [0, 1] without
  clipping information at the tails.
* **Confidence shrinkage** pulls a score toward the neutral 0.5 when the
  evidence is thin. A wallet with two lucky trades must not read as a genius;
  truth requires that certainty grow with observation.
"""

from __future__ import annotations

import math


def logistic(x: float, *, midpoint: float = 0.0, scale: float = 1.0) -> float:
    """Map ℝ → (0, 1). ``midpoint`` maps to 0.5; ``scale`` sets steepness."""
    z = (x - midpoint) / scale
    # Guard against overflow for extreme inputs.
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)


def clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def confidence(n: int, *, k: int = 20) -> float:
    """Bayesian-flavored confidence in [0, 1): ``n / (n + k)``. With ``k`` trades
    the system is "half sure"; it approaches certainty only with sustained
    observation."""
    return n / (n + k) if n > 0 else 0.0


def shrink(score: float, conf: float, *, neutral: float = 0.5) -> float:
    """Blend a raw score toward neutral by lack of confidence."""
    return clamp01(neutral + (score - neutral) * conf)


def mean_of_present(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None
