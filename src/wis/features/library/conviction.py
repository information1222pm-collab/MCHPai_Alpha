"""Conviction feature specs."""

from __future__ import annotations

from wis.features.spec import FeatureSpec

TAG = ("conviction",)


def _f(name: str, version: int, desc: str, dtype: type, fn) -> FeatureSpec:
    return FeatureSpec(name=name, version=version, dtype=dtype, description=desc, extract=fn, tags=TAG)


SPECS: list[FeatureSpec] = [
    _f("conviction.avg_position_size", 1, "Mean quote cost per trade.", float,
       lambda c: c.frame.conviction.average_position_size),
    _f("conviction.position_concentration", 1, "Herfindahl concentration over tokens.", float,
       lambda c: c.frame.conviction.position_concentration),
    _f("conviction.portfolio_diversity", 1, "1 - concentration.", float,
       lambda c: c.frame.conviction.portfolio_diversity),
    _f("conviction.distinct_tokens", 1, "Count of distinct tokens touched.", int,
       lambda c: c.frame.conviction.distinct_tokens),
    _f("conviction.scaling_behavior", 1, "Average buys per token (>1 = averaging in).", float,
       lambda c: c.frame.conviction.scaling_behavior),
    _f("conviction.diamond_hands_score", 1, "Holding-through-time proxy (0..1).", float,
       lambda c: c.frame.conviction.diamond_hands_score),
]
