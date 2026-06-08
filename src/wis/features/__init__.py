"""The Feature Factory.

Importing this package wires the built-in feature library into the default
registry, so any consumer that touches ``wis.features`` gets a fully-populated
catalog without explicit setup. New feature packs are added in
``wis.features.library``; the factory machinery (spec, registry, compiler) stays
fixed.
"""

from __future__ import annotations

# Side-effect import: registers all built-in specs into DEFAULT_REGISTRY.
from wis.features import library as library  # noqa: F401

__all__ = ["library"]
