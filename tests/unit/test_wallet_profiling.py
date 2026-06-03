"""Unit tests for FIFO round-trip matching and behavioral profiling."""

from datetime import datetime, timedelta, timezone

from mchpai_common.schemas.common import Side
from mchpai_common.schemas.trade import Trade
from mchpai_common.wallets import match_round_trips, profile_wallet

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _trade(side, sol, tok, minutes):
    return Trade(
        signature=f"sig{minutes}", wallet="W", mint="M", side=side,
        sol_amount=sol, token_amount=tok, block_time=T0 + timedelta(minutes=minutes),
    )


def test_single_profitable_round_trip():
    trades = [
        _trade(Side.buy, 1.0, 100, 0),
        _trade(Side.sell, 2.0, 100, 60),  # 2x
    ]
    rts = match_round_trips(trades)
    assert len(rts) == 1
    assert rts[0].pnl_sol == 1.0
    assert rts[0].ret == 1.0
    assert rts[0].hold_seconds == 3600


def test_fifo_partial_fills():
    trades = [
        _trade(Side.buy, 1.0, 100, 0),
        _trade(Side.buy, 1.0, 100, 10),
        _trade(Side.sell, 3.0, 150, 30),  # consumes lot1 fully + half of lot2
    ]
    rts = match_round_trips(trades)
    assert len(rts) == 2
    assert abs(sum(rt.proceeds_sol for rt in rts) - 3.0) < 1e-9


def test_profile_metrics_bounds():
    trades = [
        _trade(Side.buy, 1.0, 100, 0),
        _trade(Side.sell, 1.5, 100, 30),
        _trade(Side.buy, 1.0, 100, 40),
        _trade(Side.sell, 0.5, 100, 70),  # a loss
    ]
    p = profile_wallet("W", trades)
    assert p.closed_trades == 2
    assert 0.0 <= p.win_rate <= 1.0
    assert 0.0 <= p.profit_consistency <= 1.0
    assert p.win_rate == 0.5


def test_no_trades_returns_empty_profile():
    p = profile_wallet("W", [])
    assert p.closed_trades == 0
    assert p.roi == 0.0
