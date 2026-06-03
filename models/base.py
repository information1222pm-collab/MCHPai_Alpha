"""Model training harness — the contract every model family implements.

A ``Trainer`` pulls a ``Dataset``, fits a ``Model``, evaluates it walk-forward
(no look-ahead leakage), and publishes the artifact + manifest to the MinIO model
registry. The serving side (prediction-engine ``ModelRegistry``) only needs the
manifest + artifact, so any family — trees today, GNN/transformers tomorrow —
plugs in without changing serving.
"""

from __future__ import annotations

import abc
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Dataset:
    """A materialized training set pulled from ClickHouse feature_vectors."""

    X: list[dict[str, float]]
    y: list[float]
    feature_names: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


@dataclass
class Manifest:
    name: str               # target, e.g. "buy_probability"
    family: str             # xgboost | lightgbm | catboost | gnn | transformer | rl
    version: str
    metrics: dict[str, float]
    feature_names: list[str]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_json(self) -> str:
        return json.dumps(self.__dict__, indent=2)


class Model(abc.ABC):
    """A fitted model exposing the single serving method the platform needs."""

    @abc.abstractmethod
    def predict(self, features: dict[str, float]) -> float: ...

    @abc.abstractmethod
    def save(self, path: str) -> None: ...


class Trainer(abc.ABC):
    family: str

    @abc.abstractmethod
    def fit(self, ds: Dataset) -> Model: ...

    def evaluate(self, model: Model, ds: Dataset) -> dict[str, float]:
        """Default pointwise eval; families override with walk-forward CV."""
        preds = [model.predict(x) for x in ds.X]
        n = max(1, len(ds.y))
        mae = sum(abs(p - t) for p, t in zip(preds, ds.y)) / n
        return {"mae": mae, "n": float(n)}

    def publish(self, model: Model, manifest: Manifest, *, bucket: str = "models") -> None:
        """Persist artifact + manifest to MinIO (skeleton: local save)."""
        local = f"models/saved_models/{manifest.name}-{manifest.version}.bin"
        model.save(local)
        # Production: upload `local` + manifest.to_json() to MinIO `bucket`.
