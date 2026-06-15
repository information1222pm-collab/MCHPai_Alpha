"""Entropy & information theory — the *surprise* of on-chain flows.

A token whose buyers are many and independent carries more information than one
bought repeatedly by a single cluster. We quantify this with Shannon entropy and
related measures, turning "who is buying" into features the models can learn from.

Intuitions:
    * High buyer-entropy + rising attention  -> organic discovery (bullish).
    * Low buyer-entropy (concentrated)        -> coordinated/wash (risky).
    * KL-divergence of the current buyer mix vs. baseline -> regime change.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

import numpy as np


def shannon_entropy(counts: Iterable[float], base: float = 2.0) -> float:
    """Shannon entropy of a distribution given category counts/weights."""
    arr = np.asarray(list(counts), dtype=float)
    arr = arr[arr > 0]
    if arr.size == 0:
        return 0.0
    p = arr / arr.sum()
    return float(-np.sum(p * (np.log(p) / np.log(base))))


def normalized_entropy(counts: Iterable[float]) -> float:
    """Entropy scaled to [0,1] by the max possible (uniform) entropy."""
    arr = [c for c in counts if c > 0]
    if len(arr) <= 1:
        return 0.0
    return shannon_entropy(arr) / (np.log(len(arr)) / np.log(2.0))


def buyer_entropy(buyer_sol_amounts: dict[str, float]) -> float:
    """Normalized entropy of capital across distinct buyers of a token."""
    return normalized_entropy(buyer_sol_amounts.values())


def kl_divergence(p: dict[str, float], q: dict[str, float], eps: float = 1e-9) -> float:
    """KL(p || q) over a shared support — detects buyer-mix regime shifts."""
    keys = set(p) | set(q)
    ps = np.array([p.get(k, 0.0) for k in keys], dtype=float) + eps
    qs = np.array([q.get(k, 0.0) for k in keys], dtype=float) + eps
    ps /= ps.sum()
    qs /= qs.sum()
    return float(np.sum(ps * np.log(ps / qs)))


def flow_surprise(observed: Counter, baseline: Counter) -> float:
    """Surprise (cross-entropy gap) of an observed flow vs. a baseline."""
    return kl_divergence(dict(observed), dict(baseline))
