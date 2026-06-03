"""Transform registry — the verbs of the Feature Factory.

A transform maps (spec, context, already-resolved features) → a scalar. Window
transforms read an ordered series of a raw input key from the entity's history.
New transforms are added via :func:`register_transform` and immediately become
available to every spec — this is how the catalog scales without new glue code.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import TYPE_CHECKING

import numpy as np

from .. import entropy as entropy_lib
from .. import epidemiology as epi_lib
from .. import indicators

if TYPE_CHECKING:
    from .compiler import FeatureContext
    from .spec import FeatureSpec

Transform = Callable[["FeatureSpec", "FeatureContext", dict], float]
TRANSFORMS: dict[str, Transform] = {}
NAN = float("nan")


def register_transform(name: str) -> Callable[[Transform], Transform]:
    def deco(fn: Transform) -> Transform:
        TRANSFORMS[name] = fn
        return fn

    return deco


def _val(spec, ctx, resolved, idx=0) -> float:
    """Resolve a dependency value: a prior feature if known, else a raw input."""
    dep = spec.dependencies[idx]
    if dep in resolved:
        return resolved[dep]
    v = ctx.inputs.get(dep, NAN)
    return float(v) if isinstance(v, (int, float)) else NAN


def _series(ctx, key: str, window: int | None) -> np.ndarray:
    """Ordered series of a raw input key over history + current (most recent last)."""
    vals = [r.get(key) for r in ctx.history]
    vals.append(ctx.inputs.get(key))
    arr = np.array([float(v) for v in vals if isinstance(v, (int, float))], dtype=float)
    if window:
        arr = arr[-window:]
    return arr


# ---- passthrough & arithmetic ---------------------------------------------
@register_transform("input")
def _input(spec, ctx, resolved):
    return _val(spec, ctx, resolved)


@register_transform("ratio")
def _ratio(spec, ctx, resolved):
    a, b = _val(spec, ctx, resolved, 0), _val(spec, ctx, resolved, 1)
    return a / b if b not in (0.0, NAN) and not math.isnan(b) else 0.0


@register_transform("sum")
def _sum(spec, ctx, resolved):
    return float(sum(_val(spec, ctx, resolved, i) for i in range(len(spec.dependencies))))


@register_transform("diff")
def _diff(spec, ctx, resolved):
    return _val(spec, ctx, resolved, 0) - _val(spec, ctx, resolved, 1)


@register_transform("product")
def _product(spec, ctx, resolved):
    out = 1.0
    for i in range(len(spec.dependencies)):
        out *= _val(spec, ctx, resolved, i)
    return out


# ---- order-flow ------------------------------------------------------------
@register_transform("imbalance")
def _imbalance(spec, ctx, resolved):
    return indicators.imbalance(_val(spec, ctx, resolved, 0), _val(spec, ctx, resolved, 1))


# ---- rolling / windowed ----------------------------------------------------
@register_transform("rolling_mean")
def _rmean(spec, ctx, resolved):
    s = _series(ctx, spec.dependencies[0], spec.window)
    return float(s.mean()) if s.size else 0.0


@register_transform("rolling_sum")
def _rsum(spec, ctx, resolved):
    s = _series(ctx, spec.dependencies[0], spec.window)
    return float(s.sum()) if s.size else 0.0


@register_transform("rolling_std")
def _rstd(spec, ctx, resolved):
    s = _series(ctx, spec.dependencies[0], spec.window)
    return float(s.std(ddof=0)) if s.size else 0.0


@register_transform("rolling_max")
def _rmax(spec, ctx, resolved):
    s = _series(ctx, spec.dependencies[0], spec.window)
    return float(s.max()) if s.size else 0.0


@register_transform("rolling_min")
def _rmin(spec, ctx, resolved):
    s = _series(ctx, spec.dependencies[0], spec.window)
    return float(s.min()) if s.size else 0.0


@register_transform("zscore")
def _zscore(spec, ctx, resolved):
    s = _series(ctx, spec.dependencies[0], spec.window)
    return indicators.zscore(s) if s.size else 0.0


@register_transform("rate_of_change")
def _roc(spec, ctx, resolved):
    s = _series(ctx, spec.dependencies[0], spec.window)
    return indicators.rate_of_change(s, periods=1) if s.size else 0.0


@register_transform("ewma")
def _ewma(spec, ctx, resolved):
    s = _series(ctx, spec.dependencies[0], spec.window)
    if not s.size:
        return 0.0
    hl = spec.param("halflife", 3.0)
    return float(indicators.ewma(s, hl)[-1])


@register_transform("slope")
def _slope(spec, ctx, resolved):
    """Least-squares slope over the window (trend strength)."""
    s = _series(ctx, spec.dependencies[0], spec.window)
    if s.size < 2:
        return 0.0
    x = np.arange(s.size, dtype=float)
    return float(np.polyfit(x, s, 1)[0])


@register_transform("acceleration")
def _accel(spec, ctx, resolved):
    """Second difference of the window (is growth speeding up?)."""
    s = _series(ctx, spec.dependencies[0], spec.window)
    if s.size < 3:
        return 0.0
    return float(np.diff(s, 2)[-1])


# ---- domain-science transforms --------------------------------------------
@register_transform("r0")
def _r0(spec, ctx, resolved):
    s = _series(ctx, spec.dependencies[0], spec.window)
    return epi_lib.estimate_r0(s) if s.size >= 2 else 0.0


@register_transform("entropy_of")
def _entropy_of(spec, ctx, resolved):
    """Entropy of a distribution passed in as a list/dict input."""
    v = ctx.inputs.get(spec.dependencies[0])
    if isinstance(v, dict):
        return entropy_lib.normalized_entropy(v.values())
    if isinstance(v, (list, tuple)):
        return entropy_lib.normalized_entropy(v)
    return 0.0


@register_transform("gini_of")
def _gini_of(spec, ctx, resolved):
    v = ctx.inputs.get(spec.dependencies[0])
    if isinstance(v, (list, tuple)) and v:
        return indicators.gini(np.array(v, dtype=float))
    return 0.0
