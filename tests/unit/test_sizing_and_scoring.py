"""Unit tests for adaptive sizing and the headline scores."""

import sys
from pathlib import Path

# Make the service packages importable without installing every service.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "strategy-engine"))
sys.path.insert(0, str(ROOT / "services" / "prediction-engine"))

from strategy_engine.sizing import SizingConfig, adaptive_size  # noqa: E402
from prediction_engine import scoring  # noqa: E402
from mchpai_common.schemas.wallet import WalletProfile  # noqa: E402


def _cfg():
    return SizingConfig(bankroll_sol=10.0, kelly_fraction=0.25, min_ticket_sol=0.05,
                        max_ticket_sol=2.0, max_token_exposure_sol=4.0)


def test_sizing_zero_when_no_edge():
    assert adaptive_size(_cfg(), expected_value_bps=0.0, risk_score=10.0) == 0.0


def test_sizing_respects_max_ticket():
    size = adaptive_size(_cfg(), expected_value_bps=5000.0, risk_score=0.0, conviction=1.0)
    assert size <= 2.0


def test_sizing_shrinks_with_risk():
    low = adaptive_size(_cfg(), expected_value_bps=800.0, risk_score=10.0, conviction=0.8)
    high = adaptive_size(_cfg(), expected_value_bps=800.0, risk_score=90.0, conviction=0.8)
    assert low > high


def test_alpha_score_shrinks_small_samples():
    proven = WalletProfile(address="A", closed_trades=300, roi=2.0, win_rate=0.6,
                           profit_consistency=0.8, conviction=0.5, risk=0.2, avg_hold_seconds=1800)
    lucky = WalletProfile(address="B", closed_trades=2, roi=4.0, win_rate=1.0,
                          profit_consistency=1.0, conviction=0.5, risk=0.2, avg_hold_seconds=1800)
    sp, _ = scoring.wallet_alpha_score(proven)
    sl, _ = scoring.wallet_alpha_score(lucky)
    assert sp > sl  # proven beats lucky-2-for-2


def test_cluster_score_bounds():
    s = scoring.cluster_score([80, 70, 90], co_buy_lift=5.0, has_shared_funder=True)
    assert 0.0 <= s <= 100.0
