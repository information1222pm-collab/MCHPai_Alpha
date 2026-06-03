"""Point-in-time dataset assembly.

Joins a token's feature vector *as it was at the decision moment* (a fixed age,
e.g. 60s after birth) with its frozen ground-truth label. Using the feature
store's point-in-time read guarantees no look-ahead leakage: we never train on
features that only existed after the decision we are trying to learn.

Only ``is_final`` ground truth is used, so labels never change under the model.
"""

from __future__ import annotations

from datetime import timedelta

from mchpai_common.feature_store import FeatureStore
from mchpai_common.schemas.ground_truth import GroundTruth

from .base import Dataset
from .targets import label_for


def build_dataset(
    store: FeatureStore,
    ground_truths: list[GroundTruth],
    target: str,
    *,
    decision_age_seconds: float = 60.0,
    require_final: bool = True,
) -> Dataset:
    X: list[dict[str, float]] = []
    y: list[float] = []
    feature_names: set[str] = set()

    for gt in ground_truths:
        if require_final and not gt.is_final:
            continue
        as_of = gt.created_at + timedelta(seconds=decision_age_seconds)
        feats = store.get_point_in_time("token", gt.mint, as_of)
        if not feats:
            continue
        X.append(feats)
        y.append(label_for(target, gt))
        feature_names.update(feats.keys())

    return Dataset(
        X=X,
        y=y,
        feature_names=sorted(feature_names),
        meta={"target": target, "decision_age_seconds": decision_age_seconds, "n": len(y)},
    )
