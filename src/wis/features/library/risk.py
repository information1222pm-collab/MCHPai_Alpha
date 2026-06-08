"""Risk feature specs."""

from __future__ import annotations

from wis.features.spec import FeatureSpec

TAG = ("risk",)


def _f(name: str, version: int, desc: str, dtype: type, fn) -> FeatureSpec:
    return FeatureSpec(name=name, version=version, dtype=dtype, description=desc, extract=fn, tags=TAG)


SPECS: list[FeatureSpec] = [
    _f("risk.loss_frequency", 1, "Fraction of closed trades that lost money.", float,
       lambda c: c.frame.risk.loss_frequency),
    _f("risk.max_consecutive_losses", 1, "Longest run of losing trades.", int,
       lambda c: c.frame.risk.max_consecutive_losses),
    _f("risk.volatility_tolerance", 1, "Std-dev of trade returns.", float,
       lambda c: c.frame.risk.volatility_tolerance),
    _f("risk.tail_risk_cvar5", 1, "Mean of the worst 5% of trade returns.", float,
       lambda c: c.frame.risk.tail_risk_cvar5),
    _f("risk.rug_exposure", 1, "Exposure to rugged tokens (pending label feed).", float,
       lambda c: c.frame.risk.rug_exposure),
    _f("risk.scam_exposure", 1, "Exposure to scam tokens (pending label feed).", float,
       lambda c: c.frame.risk.scam_exposure),
]
