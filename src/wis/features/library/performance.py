"""Performance feature specs — declared over the wallet frame's metrics."""

from __future__ import annotations

from wis.features.spec import FeatureSpec

TAG = ("performance",)


def _f(name: str, version: int, desc: str, fn) -> FeatureSpec:
    return FeatureSpec(name=name, version=version, dtype=float, description=desc, extract=fn, tags=TAG)


SPECS: list[FeatureSpec] = [
    _f("perf.lifetime_roi", 1, "Realised lifetime return on cost.",
       lambda c: c.frame.performance.lifetime_roi),
    _f("perf.roi_30d", 1, "Realised ROI over the trailing 30 days.",
       lambda c: c.frame.performance.roi_30d),
    _f("perf.roi_7d", 1, "Realised ROI over the trailing 7 days.",
       lambda c: c.frame.performance.roi_7d),
    _f("perf.average_multiple", 1, "Mean proceeds/cost across closed trades.",
       lambda c: c.frame.performance.average_multiple),
    _f("perf.median_multiple", 1, "Median proceeds/cost across closed trades.",
       lambda c: c.frame.performance.median_multiple),
    _f("perf.sharpe", 1, "Per-trade Sharpe ratio of returns.",
       lambda c: c.frame.performance.sharpe_ratio),
    _f("perf.sortino", 1, "Per-trade Sortino ratio of returns.",
       lambda c: c.frame.performance.sortino_ratio),
    _f("perf.expectancy", 1, "Mean pnl per closed trade.",
       lambda c: c.frame.performance.expectancy),
    _f("perf.profit_factor", 1, "Gross profit / gross loss.",
       lambda c: c.frame.performance.profit_factor),
    _f("perf.kelly_fraction", 1, "Kelly-optimal bet fraction from win/loss profile.",
       lambda c: c.frame.performance.kelly_fraction),
    _f("perf.capital_efficiency", 1, "Total pnl per unit of average deployed capital.",
       lambda c: c.frame.performance.capital_efficiency),
    _f("perf.win_rate", 1, "Fraction of closed trades that were profitable.",
       lambda c: c.frame.performance.win_rate),
    _f("perf.max_drawdown", 1, "Largest peak-to-trough drop of cumulative pnl.",
       lambda c: c.frame.performance.max_drawdown),
    _f("perf.recovery_factor", 1, "Total pnl divided by max drawdown.",
       lambda c: c.frame.performance.recovery_factor),
]
