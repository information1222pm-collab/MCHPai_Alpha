"""Timing feature specs."""

from __future__ import annotations

from wis.features.spec import FeatureSpec

TAG = ("timing",)


def _f(name: str, version: int, desc: str, fn) -> FeatureSpec:
    return FeatureSpec(name=name, version=version, dtype=float, description=desc, extract=fn, tags=TAG)


SPECS: list[FeatureSpec] = [
    _f("timing.avg_hold_seconds", 1, "Mean holding period of closed trades.",
       lambda c: c.frame.timing.average_hold_seconds),
    _f("timing.median_hold_seconds", 1, "Median holding period of closed trades.",
       lambda c: c.frame.timing.median_hold_seconds),
    _f("timing.patience_score", 1, "Saturating measure of holding patience (0..1).",
       lambda c: c.frame.timing.patience_score),
    _f("timing.reaction_speed_seconds", 1, "Mean gap from token genesis to entry.",
       lambda c: c.frame.timing.reaction_speed_seconds),
    _f("timing.entry_percentile", 1, "Mean price-percentile rank at entry (lower=cheaper).",
       lambda c: c.frame.timing.entry_percentile),
    _f("timing.exit_percentile", 1, "Mean price-percentile rank at exit (higher=richer).",
       lambda c: c.frame.timing.exit_percentile),
]
