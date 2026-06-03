"""Tests for ground-truth label generation."""

from datetime import datetime, timezone

from mchpai_common.ground_truth import SnapshotPoint, compute_ground_truth
from mchpai_common.schemas.ground_truth import Outcome

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_achieved_multiples_and_horizons():
    pts = [
        SnapshotPoint(age_seconds=0, price_sol=1.0, liquidity_sol=100, holders=10),
        SnapshotPoint(age_seconds=600, price_sol=3.0, liquidity_sol=120, holders=50),   # 3x @10m
        SnapshotPoint(age_seconds=5000, price_sol=12.0, liquidity_sol=150, holders=80),  # 12x <6h
    ]
    gt = compute_ground_truth("M", T0, pts)
    assert gt.reference_price == 1.0
    assert gt.max_multiple == 12.0
    assert gt.label(2, "1h") is True
    assert gt.label(10, "6h") is True
    assert gt.label(25, "6h") is False
    assert gt.max_multiple_by_horizon["1h"] == 3.0


def test_rug_detection():
    pts = [
        SnapshotPoint(age_seconds=0, price_sol=1.0, liquidity_sol=100, holders=100),
        SnapshotPoint(age_seconds=120, price_sol=2.0, liquidity_sol=200, holders=150),
        SnapshotPoint(age_seconds=300, price_sol=0.01, liquidity_sol=1.0, holders=20),  # LP pulled
    ]
    gt = compute_ground_truth("M", T0, pts)
    assert gt.outcome == Outcome.rugged
    assert gt.rugged_at is not None
    assert gt.survival_seconds == 300


def test_viral_outcome():
    pts = [
        SnapshotPoint(age_seconds=0, price_sol=1.0, liquidity_sol=100, holders=100),
        SnapshotPoint(age_seconds=3600, price_sol=15.0, liquidity_sol=300, holders=500),
        SnapshotPoint(age_seconds=90000, price_sol=20.0, liquidity_sol=350, holders=800),  # >24h
    ]
    gt = compute_ground_truth("M", T0, pts)
    assert gt.outcome == Outcome.viral
    assert gt.max_multiple == 20.0


def test_empty_sequence_is_safe():
    gt = compute_ground_truth("M", T0, [])
    assert gt.outcome == Outcome.pending
    assert gt.max_multiple == 1.0
