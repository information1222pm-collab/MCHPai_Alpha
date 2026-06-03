"""Tests for the dataset quality & integrity checks (Phase 3 empirical QA)."""

from datetime import datetime, timedelta, timezone

from mchpai_common.feature_factory import FeatureCompiler, build_default_catalog
from mchpai_common.quality import (
    DatasetQualityReport,
    Status,
    assert_causal,
    boundary_aligned,
    coverage,
    feature_drift_psi,
    find_duplicate_births,
    find_slot_gaps,
    label_maturity,
    null_rate,
    online_offline_divergence,
    psi,
    replay_consistent,
    sequence_integrity,
    total_slot_gap,
)
from mchpai_common.schemas.common import Side
from mchpai_common.schemas.swap import Dex, SwapEvent
from mchpai_common.timelines import WalletStateReducer

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


# ---- integrity -------------------------------------------------------------
def test_slot_gaps():
    assert find_slot_gaps([100, 101, 102]) == []
    assert find_slot_gaps([100, 105]) == [(101, 104)]
    assert total_slot_gap([100, 105, 106]) == 4


def test_duplicate_births_must_be_zero():
    assert find_duplicate_births(["a", "b", "c"]) == []
    assert set(find_duplicate_births(["a", "a", "b", "b", "c"])) == {"a", "b"}


def test_sequence_integrity():
    ok = sequence_integrity([0, 1, 2, 3])
    assert ok.ok and ok.monotonic
    bad = sequence_integrity([0, 1, 1, 3])  # dup + gap
    assert not bad.ok
    assert 1 in bad.duplicates


def test_boundary_alignment():
    assert boundary_aligned(1_000_000, 5)       # divisible by 5
    assert not boundary_aligned(1_000_003, 5)


def test_replay_determinism_true_for_pure_reducer():
    events = [
        SwapEvent(signature=f"s{i}", slot=i, timestamp=T0 + timedelta(seconds=i),
                  dex=Dex.unknown, wallet_address="W", token_address="M",
                  side=Side.buy if i % 2 == 0 else Side.sell,
                  sol_amount=1.0 + i, token_amount=100.0, price=0.01)
        for i in range(15)
    ]
    assert replay_consistent(events, lambda: WalletStateReducer("W"), lambda r, e: r.apply(e))


def test_replay_detects_nondeterminism():
    import random

    class Flaky:
        def apply(self, e):
            return {"v": random.random()}  # non-deterministic on purpose

    events = list(range(5))
    assert not replay_consistent(events, lambda: Flaky(), lambda r, e: r.apply(e))


def test_feature_causality_no_leakage():
    compiler = FeatureCompiler(build_default_catalog())
    rows = [
        {m: float(i + 1) for m in (
            "price_sol", "volume_sol", "liquidity_sol", "market_cap_sol", "buyers",
            "sellers", "unique_traders", "holders", "txns", "net_flow_sol",
            "entropy", "smart_money_ratio", "cluster_ratio")}
        for i in range(10)
    ]
    assert assert_causal(compiler, rows) is True  # the catalog must be causal


def test_online_offline_divergence():
    a = {"f1": 1.0, "f2": 2.0}
    b = {"f1": 1.0, "f2": 2.0}
    assert max(online_offline_divergence(a, b).values()) == 0.0
    c = {"f1": 1.0, "f2": 2.5}
    assert online_offline_divergence(a, c)["f2"] == 0.5


# ---- metrics ---------------------------------------------------------------
def test_coverage():
    assert coverage(100, 100) == 1.0
    assert coverage(100, 50) == 0.5
    assert coverage(0, 0) == 1.0


def test_null_rate():
    vecs = [{"a": 1.0, "b": 0.0}, {"a": 0.0, "b": 0.0}]
    nr = null_rate(vecs)
    assert nr["a"] == 0.5 and nr["b"] == 1.0


def test_label_maturity():
    assert label_maturity([True, True, False, False]) == 0.5
    assert label_maturity([]) == 0.0


def test_psi_stable_vs_shifted():
    ref = list(range(1000))
    same = list(range(1000))
    shifted = list(range(2000, 3000))
    assert psi(ref, same) < 0.1            # stable
    assert psi(ref, shifted) > 0.25        # significant shift


def test_feature_drift_psi():
    ref = [{"x": float(i)} for i in range(100)]
    cur = [{"x": float(i) + 500} for i in range(100)]
    drift = feature_drift_psi(ref, cur)
    assert drift["x"] > 0.25


# ---- report rollup ---------------------------------------------------------
def test_report_status_rollup():
    green = DatasetQualityReport()
    assert green.status() == Status.green

    red = DatasetQualityReport(duplicate_births=1)
    assert red.status() == Status.red

    red2 = DatasetQualityReport(feature_leakage=True)
    assert red2.status() == Status.red

    yellow = DatasetQualityReport(max_feature_psi=0.4)
    assert yellow.status() == Status.yellow
