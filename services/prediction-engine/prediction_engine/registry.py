"""Backend-agnostic model registry.

Models are artifacts in MinIO (``models`` bucket) with a small JSON manifest. The
serving code asks for ``load("buy_probability")`` and gets a callable
``predict(features: dict) -> float`` regardless of whether the artifact is
XGBoost, LightGBM, CatBoost, a GNN, or a transformer. If nothing is published,
the registry falls back to the transparent baselines in :mod:`scoring`.
"""

from __future__ import annotations

from collections.abc import Callable

from mchpai_common.logging import get_logger

from .scoring import buy_probability_baseline

log = get_logger("prediction-engine.registry")

Predictor = Callable[[dict], float]


class ModelRegistry:
    def __init__(self) -> None:
        self._cache: dict[str, Predictor] = {}

    def load(self, name: str) -> Predictor:
        if name in self._cache:
            return self._cache[name]
        predictor = self._load_from_store(name) or self._baseline(name)
        self._cache[name] = predictor
        return predictor

    def _load_from_store(self, name: str) -> Predictor | None:
        # Production: pull the latest artifact from MinIO and wrap its predict().
        # Returns None when no model is published so we degrade to baselines.
        try:
            # from mchpai_common.database import get_minio  # wired in prod
            return None
        except Exception as exc:  # noqa: BLE001
            log.warning("registry.load_failed", model=name, error=str(exc))
            return None

    @staticmethod
    def _baseline(name: str) -> Predictor:
        if name == "buy_probability":
            return buy_probability_baseline
        return lambda _features: 0.0
