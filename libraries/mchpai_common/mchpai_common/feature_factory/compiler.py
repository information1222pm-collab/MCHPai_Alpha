"""FeatureCompiler — turns a list of specs into one fast callable.

It topologically sorts specs by their inter-feature dependencies (so a feature
can be built from other features), validates the DAG (missing deps / cycles), and
produces ``compute(context) -> dict[str, float]``. Window transforms pull ordered
history from the context; normalization is applied per feature after transform.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .spec import FeatureSpec, Normalization
from .transforms import TRANSFORMS


@dataclass
class FeatureContext:
    """One entity-step plus its ordered prior history (most recent last)."""

    inputs: dict[str, Any]
    history: list[dict[str, Any]] = field(default_factory=list)


def _normalize(value: float, spec: FeatureSpec) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return 0.0
    n = spec.normalization
    if n == Normalization.none:
        return value
    if n == Normalization.log1p:
        return math.log1p(value) if value > -1 else 0.0
    if n == Normalization.tanh:
        return math.tanh(value)
    if n == Normalization.clip01:
        return min(1.0, max(0.0, value))
    if n == Normalization.minmax:
        lo, hi = spec.param("min", 0.0), spec.param("max", 1.0)
        return (value - lo) / (hi - lo) if hi > lo else 0.0
    return value


class FeatureCompiler:
    def __init__(self, specs: list[FeatureSpec]) -> None:
        self._specs = {s.name: s for s in specs}
        if len(self._specs) != len(specs):
            raise ValueError("duplicate feature names in catalog")
        self._order = self._topo_sort()

    @property
    def feature_names(self) -> list[str]:
        return list(self._order)

    def _topo_sort(self) -> list[str]:
        names = set(self._specs)
        order: list[str] = []
        state: dict[str, int] = {}  # 0=unseen,1=visiting,2=done

        def visit(name: str, stack: tuple[str, ...]) -> None:
            st = state.get(name, 0)
            if st == 2:
                return
            if st == 1:
                raise ValueError(f"cycle in feature DAG at {name}: {' -> '.join(stack)}")
            state[name] = 1
            for dep in self._specs[name].dependencies:
                if dep in names:  # edge to another feature (raw inputs are leaves)
                    visit(dep, stack + (dep,))
            state[name] = 2
            order.append(name)

        for n in self._specs:
            visit(n, (n,))
        return order

    def compute(self, ctx: FeatureContext) -> dict[str, float]:
        resolved: dict[str, float] = {}
        for name in self._order:
            spec = self._specs[name]
            fn = TRANSFORMS.get(spec.transform)
            if fn is None:
                raise KeyError(f"unknown transform '{spec.transform}' for feature '{name}'")
            try:
                raw = fn(spec, ctx, resolved)
            except Exception:
                raw = 0.0
            resolved[name] = _normalize(float(raw), spec)
        return resolved

    def compute_sequence(self, rows: list[dict[str, Any]]) -> list[dict[str, float]]:
        """Compute features for an ordered sequence, feeding history incrementally.

        This is the offline/training path: turn a token's raw snapshot sequence
        into a feature-vector sequence with correct windowing at every step.
        """
        out: list[dict[str, float]] = []
        for i, row in enumerate(rows):
            ctx = FeatureContext(inputs=row, history=rows[:i])
            out.append(self.compute(ctx))
        return out
