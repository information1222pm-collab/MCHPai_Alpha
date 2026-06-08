"""The FeatureCompiler — turns a wallet frame into a feature vector.

The compiler is deliberately thin: it owns *consistency*, not computation. It
runs each registered spec's pure ``extract`` over a single point-in-time frame
and assembles a versioned :class:`FeatureVector`. Because both the offline
(backfill) and online (serving) paths call the very same method on the very same
kind of frame, training/serving skew is structurally impossible.
"""

from __future__ import annotations

from dataclasses import dataclass

from wis.domain.identifiers import WalletAddress
from wis.domain.time import Nanos, Sequence
from wis.domain.wallet.state import WalletFrame
from wis.features.registry import DEFAULT_REGISTRY, FeatureRegistry
from wis.features.spec import FeatureContext, FeatureValue


@dataclass(frozen=True, slots=True)
class FeatureVector:
    address: WalletAddress
    as_of_sequence: Sequence
    as_of_time: Nanos
    values: dict[str, FeatureValue]

    def get(self, key: str) -> object | None:
        v = self.values.get(key)
        return v.value if v is not None else None

    @property
    def null_keys(self) -> list[str]:
        return [k for k, v in self.values.items() if v.is_null]


class FeatureCompiler:
    def __init__(self, registry: FeatureRegistry | None = None) -> None:
        self._registry = registry if registry is not None else DEFAULT_REGISTRY

    def compile(self, frame: WalletFrame) -> FeatureVector:
        ctx = FeatureContext(frame=frame)
        values: dict[str, FeatureValue] = {}
        for spec in self._registry:
            try:
                raw = spec.extract(ctx)
            except Exception as exc:  # a broken spec must not corrupt the vector
                raise FeatureComputationError(spec.key, exc) from exc
            values[spec.key] = FeatureValue.of(spec.key, raw)
        return FeatureVector(
            address=frame.address,
            as_of_sequence=frame.as_of_sequence,
            as_of_time=frame.as_of_time,
            values=values,
        )


class FeatureComputationError(RuntimeError):
    def __init__(self, key: str, cause: Exception) -> None:
        super().__init__(f"feature {key} failed: {cause!r}")
        self.key = key
