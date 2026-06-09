"""The daily scrape's qualification filter and time guard are pure and tested;
the network discovery/observation is exercised live by the scheduled job."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from wis.jobs.daily_scrape import ScrapeConfig, is_active, is_strong, qualifies
from wis.jobs.runner import is_eastern_midnight
from wis.ratings.model import WalletRating

CFG = ScrapeConfig()


def _rating(**kw) -> WalletRating:
    base = {
        "wallet": "w", "closed_trades": 20, "distinct_tokens": 8, "open_positions": 1, "confidence": 0.5,
        "win_rate": 0.7, "median_multiple": 1.4, "average_multiple": 1.6, "sharpe": 1.2,
        "alpha_score": 0.6, "expected_value_score": 0.6, "conviction_score": 0.5, "risk_score": 0.6,
        "timing_score": 0.5, "primary_quote": "SOL", "pnl_by_quote": {"SOL": 5.0}, "roi_by_quote": {"SOL": 0.3},
        "active_days": 3.0, "trades_per_day": 6.7,
    }
    base.update(kw)
    return WalletRating(**base)


def test_active_and_strong_qualifies() -> None:
    assert qualifies(_rating(), CFG)


def test_inactive_is_rejected() -> None:
    assert not is_active(_rating(trades_per_day=2.0), CFG)        # too few trades/day
    assert not is_active(_rating(closed_trades=3), CFG)           # too few trades
    assert not qualifies(_rating(trades_per_day=1.0), CFG)


def test_weak_performance_is_rejected() -> None:
    assert not is_strong(_rating(alpha_score=0.4), CFG)           # alpha below floor
    assert not is_strong(_rating(confidence=0.05), CFG)           # too little evidence
    assert not is_strong(_rating(roi_by_quote={"SOL": -0.1}), CFG)  # negative ROI
    assert not qualifies(_rating(alpha_score=None), CFG)


def test_eastern_midnight_guard() -> None:
    ny = ZoneInfo("America/New_York")
    assert is_eastern_midnight(datetime(2026, 6, 9, 0, 30, tzinfo=ny))
    assert not is_eastern_midnight(datetime(2026, 6, 9, 12, 0, tzinfo=ny))
    # A UTC instant that is 00:30 in New York (04:30 UTC during EDT) qualifies.
    assert is_eastern_midnight(datetime(2026, 6, 9, 4, 30, tzinfo=ZoneInfo("UTC")))
