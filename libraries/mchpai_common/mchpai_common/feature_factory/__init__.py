"""Feature Factory — a machine that *generates* features, not features.

Instead of hand-writing feature code, you declare :class:`FeatureSpec`s
(name, dependencies, window, transform, normalization, description). The
:class:`FeatureCompiler` resolves the dependency DAG and compiles them into a
single callable that, given a row + its history, emits every feature. This lets
the catalog grow 5 → 50 → 500 → 5,000+ features from compact declarations and
makes features versioned, introspectable, and reproducible.

Design goals (decades of research):
  * **Declarative** — features are data (specs), not code.
  * **Composable** — a feature may depend on raw inputs *or* other features.
  * **Windowed** — rolling transforms over an entity's ordered history.
  * **Introspectable** — every feature has a description, deps, and version.
  * **Backend-agnostic** — the same specs serve online (Redis) and offline (MinIO).
"""

from .spec import FeatureSpec, Normalization
from .transforms import TRANSFORMS, register_transform
from .compiler import FeatureCompiler, FeatureContext
from .catalog import build_default_catalog

__all__ = [
    "FeatureSpec",
    "Normalization",
    "TRANSFORMS",
    "register_transform",
    "FeatureCompiler",
    "FeatureContext",
    "build_default_catalog",
]
