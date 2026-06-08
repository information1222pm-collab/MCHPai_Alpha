"""The built-in feature library.

Importing this package registers every built-in :class:`FeatureSpec` into the
process-wide :data:`DEFAULT_REGISTRY`. This is the seed of a catalog the charter
expects to grow past 5,000 features; new packs are added here, never by editing
existing specs in place.
"""

from __future__ import annotations

from wis.features.library import conviction, performance, risk, timing
from wis.features.registry import DEFAULT_REGISTRY, FeatureRegistry
from wis.features.spec import FeatureSpec

ALL_SPECS: list[FeatureSpec] = [
    *performance.SPECS,
    *timing.SPECS,
    *conviction.SPECS,
    *risk.SPECS,
]


def load_builtin_features(registry: FeatureRegistry = DEFAULT_REGISTRY) -> FeatureRegistry:
    """Idempotently register the built-ins (safe to call once at startup)."""
    existing = {s.key for s in registry}
    registry.register_all([s for s in ALL_SPECS if s.key not in existing])
    return registry


# Populate the default registry on import so consumers get a ready catalog.
load_builtin_features()
