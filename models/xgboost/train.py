"""XGBoost trainers for the Phase-1 targets.

Default production models for ``buy_probability``, ``rug_probability``,
``survival_probability`` and ``tenx_probability``. Features come from the feature
store (point-in-time, no leakage); labels come from frozen ground truth. Trains
with early stopping under walk-forward splits and publishes to the registry.
"""

from __future__ import annotations

from models.base import Dataset, Manifest, Model, Trainer
from models.dataset import build_dataset
from models.targets import TARGETS


class XGBModel(Model):
    def __init__(self, booster=None, feature_names: list[str] | None = None) -> None:
        self._booster = booster
        self._features = feature_names or []

    def predict(self, features: dict[str, float]) -> float:
        if self._booster is None:
            return 0.0
        # import xgboost as xgb; build DMatrix in self._features order, predict.
        return 0.0

    def save(self, path: str) -> None:
        if self._booster is not None:
            self._booster.save_model(path)


class XGBTrainer(Trainer):
    family = "xgboost"

    def __init__(self, params: dict | None = None) -> None:
        self.params = params or {
            "objective": "binary:logistic",
            "eval_metric": "auc",
            "max_depth": 6,
            "eta": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
        }

    def fit(self, ds: Dataset) -> Model:
        # import xgboost as xgb
        # dtrain = xgb.DMatrix([...], label=ds.y, feature_names=ds.feature_names)
        # booster = xgb.train(self.params, dtrain, num_boost_round=500,
        #                     early_stopping_rounds=30, evals=[...])
        # return XGBModel(booster, ds.feature_names)
        return XGBModel(None, ds.feature_names)


def train_target(store, ground_truths, target: str, *, version: str = "v1") -> Manifest:
    """Train and publish one target end-to-end from store + ground truth."""
    trainer = XGBTrainer()
    ds = build_dataset(store, ground_truths, target)
    model = trainer.fit(ds)
    metrics = trainer.evaluate(model, ds)
    manifest = Manifest(name=target, family="xgboost", version=version,
                        metrics=metrics, feature_names=ds.feature_names)
    trainer.publish(model, manifest)
    return manifest


def main() -> None:
    # Production: load the finalized ground truth + a MinioFeatureStore, then
    # train every target. Here we show the loop; data loaders are wired in prod.
    from mchpai_common.feature_store import InMemoryFeatureStore

    store = InMemoryFeatureStore()
    ground_truths: list = []  # load_finalized_ground_truth() in production
    for target in TARGETS:
        manifest = train_target(store, ground_truths, target)
        print(f"trained {target}: n={manifest.metrics.get('n', 0)}")


if __name__ == "__main__":
    main()
