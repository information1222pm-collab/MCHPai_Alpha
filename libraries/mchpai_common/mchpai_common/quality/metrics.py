"""Soft quality metrics — observatory health tracked over time."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def coverage(expected: float, observed: float) -> float:
    """observed / expected, clamped to [0, 1] (event/snapshot completeness)."""
    if expected <= 0:
        return 1.0
    return float(min(1.0, max(0.0, observed / expected)))


def null_rate(vectors: list[dict[str, float]]) -> dict[str, float]:
    """Per-feature share of null/zero values across a sample of vectors."""
    if not vectors:
        return {}
    keys: set[str] = set()
    for v in vectors:
        keys.update(v.keys())
    n = len(vectors)
    out: dict[str, float] = {}
    for k in keys:
        nulls = sum(1 for v in vectors if v.get(k) in (None, 0, 0.0))
        out[k] = nulls / n
    return out


def label_maturity(is_final_flags: Sequence[bool]) -> float:
    """Fraction of ground-truth labels that are finalized (leak-free)."""
    if not is_final_flags:
        return 0.0
    return float(sum(1 for f in is_final_flags if f) / len(is_final_flags))


def psi(reference: Sequence[float], actual: Sequence[float], *, bins: int = 10, eps: float = 1e-6) -> float:
    """Population Stability Index between a reference and current distribution.

    <0.1 stable · 0.1–0.25 moderate shift · >0.25 significant shift.
    Bin edges come from reference quantiles so the metric is distribution-aware.
    """
    ref = np.asarray(reference, dtype=float)
    act = np.asarray(actual, dtype=float)
    if ref.size == 0 or act.size == 0:
        return 0.0
    quantiles = np.linspace(0, 100, bins + 1)
    edges = np.unique(np.percentile(ref, quantiles))
    if edges.size < 2:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    ref_hist, _ = np.histogram(ref, bins=edges)
    act_hist, _ = np.histogram(act, bins=edges)
    ref_pct = ref_hist / max(ref.size, 1) + eps
    act_pct = act_hist / max(act.size, 1) + eps
    return float(np.sum((act_pct - ref_pct) * np.log(act_pct / ref_pct)))


def feature_drift_psi(
    reference: list[dict[str, float]], current: list[dict[str, float]], *, bins: int = 10
) -> dict[str, float]:
    """PSI per feature between a reference window and the current window."""
    keys: set[str] = set()
    for v in reference + current:
        keys.update(v.keys())
    out: dict[str, float] = {}
    for k in keys:
        ref = [float(v[k]) for v in reference if k in v]
        cur = [float(v[k]) for v in current if k in v]
        if ref and cur:
            out[k] = psi(ref, cur, bins=bins)
    return out
