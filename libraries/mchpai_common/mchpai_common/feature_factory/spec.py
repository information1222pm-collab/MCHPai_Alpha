"""The declarative unit of the Feature Factory."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Normalization(str, Enum):
    none = "none"
    log1p = "log1p"
    tanh = "tanh"
    minmax = "minmax"     # requires params {"min","max"}
    clip01 = "clip01"


@dataclass(frozen=True)
class FeatureSpec:
    """A single declarative feature definition.

    ``dependencies`` are either raw input keys (leaves) or the names of other
    features (edges in the DAG). ``window`` (in history steps) is used by rolling
    transforms. ``transform`` names a function registered in
    :data:`~mchpai_common.feature_factory.transforms.TRANSFORMS`.
    """

    name: str
    transform: str
    dependencies: tuple[str, ...] = ()
    window: int | None = None
    params: tuple[tuple[str, float], ...] = ()       # frozen kv for hashability
    normalization: Normalization = Normalization.none
    description: str = ""
    version: str = "v1"
    tags: tuple[str, ...] = ()

    def param(self, key: str, default: float = 0.0) -> float:
        for k, v in self.params:
            if k == key:
                return v
        return default
