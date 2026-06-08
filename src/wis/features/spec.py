"""Declarative feature specifications.

A feature is *declared*, not hand-coded at each call site. A :class:`FeatureSpec`
states a feature's identity (name + version), its type, a human description, the
behavioral tags it belongs to, and a single pure ``extract`` function from a
:class:`FeatureContext` to a value (or ``None`` when not yet observable).

The design targets thousands of features without thousands of code paths:

* **Point-in-time correct & leak-free by construction.** A spec can only read a
  :class:`WalletFrame`, and a frame is *always* the result of a point-in-time
  replay (``as_of`` T). There is no API by which a feature could reach data from
  the future — the leak is impossible, not merely discouraged.
* **Online/offline consistent.** The same ``extract`` function runs whether the
  frame came from a batch backfill or a live projection, so training-time and
  serving-time values cannot diverge.
* **Versioned.** ``(name, version)`` identifies a feature forever; changing the
  computation means bumping the version, never silently redefining history.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from wis.domain.wallet.state import WalletFrame

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class FeatureContext:
    """The complete, point-in-time-bounded world a feature may observe.

    Today this is just the wallet frame; it is a struct (not the frame itself)
    so graph/cluster context can be added later without touching every spec.
    """

    frame: WalletFrame


@dataclass(frozen=True, slots=True)
class FeatureSpec(Generic[T]):
    name: str
    version: int
    dtype: type
    description: str
    extract: Callable[[FeatureContext], T | None]
    tags: tuple[str, ...] = ()
    point_in_time: bool = True

    @property
    def key(self) -> str:
        """Stable wire/storage key, e.g. ``perf.lifetime_roi@1``."""
        return f"{self.name}@{self.version}"


@dataclass(frozen=True, slots=True)
class FeatureValue:
    key: str
    value: object | None
    is_null: bool

    @classmethod
    def of(cls, key: str, value: object | None) -> FeatureValue:
        return cls(key=key, value=value, is_null=value is None)


def feature(
    name: str,
    version: int,
    dtype: type,
    description: str,
    *,
    tags: tuple[str, ...] = (),
) -> Callable[[Callable[[FeatureContext], object | None]], FeatureSpec]:
    """Decorator sugar for declaring a feature from its extract function."""

    def wrap(fn: Callable[[FeatureContext], object | None]) -> FeatureSpec:
        return FeatureSpec(
            name=name,
            version=version,
            dtype=dtype,
            description=description,
            extract=fn,
            tags=tags,
        )

    return wrap
