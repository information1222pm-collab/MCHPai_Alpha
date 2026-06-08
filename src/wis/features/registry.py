"""The feature registry — the catalog of everything the system can measure.

A single, append-only namespace of :class:`FeatureSpec` objects keyed by name.
It is the contract between the feature factory and every consumer (research
labs, scoring, future GNN/TFT training). Duplicate names are rejected so two
features can never silently collide; evolving a feature means a new *version* of
the same name, registered alongside the old.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from wis.features.spec import FeatureSpec


class FeatureRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, FeatureSpec] = {}

    def register(self, spec: FeatureSpec) -> FeatureSpec:
        if spec.key in self._specs:
            raise ValueError(f"Feature {spec.key} already registered")
        self._specs[spec.key] = spec
        return spec

    def register_all(self, specs: Iterable[FeatureSpec]) -> None:
        for spec in specs:
            self.register(spec)

    def get(self, key: str) -> FeatureSpec:
        return self._specs[key]

    def by_tag(self, tag: str) -> list[FeatureSpec]:
        return [s for s in self._specs.values() if tag in s.tags]

    def __iter__(self) -> Iterator[FeatureSpec]:
        return iter(self._specs.values())

    def __len__(self) -> int:
        return len(self._specs)


# The process-wide default registry. The built-in library populates it on import.
DEFAULT_REGISTRY = FeatureRegistry()
