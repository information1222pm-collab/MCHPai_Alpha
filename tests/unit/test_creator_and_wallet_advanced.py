"""Tests for creator intelligence and advanced wallet profiling."""

from datetime import datetime, timedelta, timezone

from mchpai_common.creators import TokenLaunch, build_creator_profile
from mchpai_common.schemas.common import Side
from mchpai_common.schemas.trade import Trade
from mchpai_common.wallets import profile_wallet_advanced

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_creator_score_penalizes_ruggers():
    serial_rugger = build_creator_profile("R", [
        TokenLaunch(mint=f"m{i}", rugged=True, max_multiple=1.0, survival_seconds=300)
        for i in range(5)
    ])
    builder = build_creator_profile("B", [
        TokenLaunch(mint=f"b{i}", rugged=False, max_multiple=8.0,
                    survival_seconds=600000, holder_retention=0.7,
                    total_buyers=100, repeat_buyers=40)
        for i in range(5)
    ])
    assert serial_rugger.rug_rate > builder.rug_rate
    assert builder.creator_score > serial_rugger.creator_score
    assert 0 <= serial_rugger.creator_score <= 100
    assert builder.best_multiple == 8.0


def test_creator_empty_history():
    p = build_creator_profile("X", [])
    assert p.launch_count == 0 and p.creator_score == 0.0


def _t(side, sol, tok, minutes, mint="M", price=None):
    return Trade(signature=f"s{minutes}{mint}", wallet="W", mint=mint, side=side,
                 sol_amount=sol, token_amount=tok, price_sol=price,
                 block_time=T0 + timedelta(minutes=minutes))


def test_advanced_profile_metrics():
    trades = [
        _t(Side.buy, 1.0, 100, 0), _t(Side.sell, 2.0, 100, 60),     # +1
        _t(Side.buy, 1.0, 100, 70), _t(Side.sell, 1.5, 100, 130),   # +0.5
        _t(Side.buy, 1.0, 100, 140), _t(Side.sell, 0.6, 100, 200),  # -0.4
    ]
    p = profile_wallet_advanced("W", trades)
    assert p.closed_trades == 3
    assert 0.0 <= p.wallet_alpha_score <= 100.0
    assert 0.0 <= p.kelly_fraction <= 1.0
    assert abs(p.win_rate - (2 / 3)) < 1e-9
    assert p.expectancy_sol > 0


def test_rug_avoidance():
    trades = [_t(Side.buy, 1.0, 100, 0, mint="GOOD"),
              _t(Side.sell, 1.2, 100, 30, mint="GOOD"),
              _t(Side.buy, 1.0, 100, 40, mint="RUG"),
              _t(Side.sell, 0.1, 100, 50, mint="RUG")]
    clean = profile_wallet_advanced("W", trades, rug_mints=set())
    exposed = profile_wallet_advanced("W", trades, rug_mints={"RUG"})
    assert clean.rug_avoidance == 1.0
    assert exposed.rug_avoidance == 0.5
