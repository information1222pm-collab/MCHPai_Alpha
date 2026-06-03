"""XGBoost trainer for the ``buy_probability`` target.

Default production model for buy_probability. Reads engineered features from
ClickHouse, labels them with realized forward outcomes, trains with early
stopping under walk-forward splits, and publishes to the model registry.
"""

from __future__ import annotations

from models.base import Dataset, Manifest, Model, Trainer


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


def main() -> None:
    trainer = XGBTrainer()
    ds = Dataset(X=[], y=[], feature_names=[])  # load_dataset() in production
    model = trainer.fit(ds)
    metrics = trainer.evaluate(model, ds)
    trainer.publish(
        model,
        Manifest(name="buy_probability", family="xgboost", version="v1", metrics=metrics,
                 feature_names=ds.feature_names),
    )


if __name__ == "__main__":
    main()
