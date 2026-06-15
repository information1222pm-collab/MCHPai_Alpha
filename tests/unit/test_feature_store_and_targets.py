"""Tests for the feature store (point-in-time, sequence) and ML targets."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))  # make `models` importable as a namespace package

from mchpai_common.feature_store import FeatureRecord, InMemoryFeatureStore  # noqa: E402
from mchpai_common.schemas.ground_truth import GroundTruth, Outcome  # noqa: E402
from models.dataset import build_dataset  # noqa: E402
from models.targets import label_for  # noqa: E402

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_point_in_time_no_lookahead():
    store = InMemoryFeatureStore()
    store.write(FeatureRecord("token", "M", T0, 0, {"f": 1.0}))
    store.write(FeatureRecord("token", "M", T0 + timedelta(seconds=60), 1, {"f": 2.0}))
    store.write(FeatureRecord("token", "M", T0 + timedelta(seconds=120), 2, {"f": 3.0}))

    # as of 70s, we must only see the vector written at 60s (f=2.0), never 120s
    pit = store.get_point_in_time("token", "M", T0 + timedelta(seconds=70))
    assert pit == {"f": 2.0}
    assert store.get_online("token", "M") == {"f": 3.0}
    assert len(store.get_sequence("token", "M")) == 3


def test_sequence_is_ordered():
    store = InMemoryFeatureStore()
    # insert out of order; store must keep them sorted by ts
    store.write(FeatureRecord("token", "M", T0 + timedelta(seconds=120), 2, {"f": 3.0}))
    store.write(FeatureRecord("token", "M", T0, 0, {"f": 1.0}))
    seq = store.get_sequence("token", "M")
    assert [r.features["f"] for r in seq] == [1.0, 3.0]


def _gt(mint, outcome, ten_x_24h=False, two_x_6h=False, survival=100000.0):
    gt = GroundTruth(mint=mint, created_at=T0, outcome=outcome,
                     survival_seconds=survival, is_final=True)
    gt.achieved = {f"{m}x": {h: False for h in ("1h", "6h", "24h", "7d")}
                   for m in (2, 5, 10, 25, 100)}
    gt.achieved["10x"]["24h"] = ten_x_24h
    gt.achieved["2x"]["6h"] = two_x_6h
    return gt


def test_target_labels():
    rug = _gt("R", Outcome.rugged, survival=1800.0)
    viral = _gt("V", Outcome.viral, ten_x_24h=True, two_x_6h=True)
    assert label_for("rug_probability", rug) == 1.0
    assert label_for("survival_probability", viral) == 1.0
    assert label_for("tenx_probability", viral) == 1.0
    assert label_for("buy_probability", viral) == 1.0
    assert label_for("buy_probability", rug) == 0.0  # early rug disqualifies


def test_build_dataset_joins_pit_features_with_labels():
    store = InMemoryFeatureStore()
    store.write(FeatureRecord("token", "V", T0, 0, {"creator_score": 80.0}))
    store.write(FeatureRecord("token", "V", T0 + timedelta(seconds=60), 1, {"creator_score": 80.0}))
    store.write(FeatureRecord("token", "R", T0, 0, {"creator_score": 10.0}))
    store.write(FeatureRecord("token", "R", T0 + timedelta(seconds=60), 1, {"creator_score": 10.0}))

    gts = [_gt("V", Outcome.viral, ten_x_24h=True), _gt("R", Outcome.rugged, survival=1800.0)]
    ds = build_dataset(store, gts, "rug_probability", decision_age_seconds=60)
    assert ds.meta["n"] == 2
    # rug token labeled 1.0, viral labeled 0.0
    labels = dict(zip([x["creator_score"] for x in ds.X], ds.y))
    assert labels[10.0] == 1.0 and labels[80.0] == 0.0
