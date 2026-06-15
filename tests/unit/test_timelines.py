"""Tests for temporal state reducers (wallet/creator/graph) and trajectory."""

from datetime import datetime, timedelta, timezone

from mchpai_common.schemas.common import Side
from mchpai_common.schemas.snapshot import LifecyclePhase, TokenSnapshot, Window
from mchpai_common.schemas.swap import Dex, SwapEvent
from mchpai_common.timelines import (
    CreatorStateReducer,
    GraphStateReducer,
    WalletStateReducer,
    build_trajectory,
)

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _swap(side, sol, tok, minutes, mint="M", price=None):
    return SwapEvent(
        signature=f"s{minutes}", slot=minutes, timestamp=T0 + timedelta(minutes=minutes),
        dex=Dex.unknown, wallet_address="W", token_address=mint, side=side,
        sol_amount=sol, token_amount=tok, price=price,
    )


def test_wallet_state_tracks_pnl_and_exposure():
    r = WalletStateReducer("W")
    s1 = r.apply(_swap(Side.buy, 1.0, 100, 0))
    assert s1.seq == 0 and s1.open_positions == 1
    assert abs(s1.exposure_sol - 1.0) < 1e-9
    s2 = r.apply(_swap(Side.sell, 2.0, 100, 10))   # close for +1 realized
    assert abs(s2.realized_pnl_sol - 1.0) < 1e-9
    assert s2.open_positions == 0
    assert s2.trade_count == 2
    assert abs(s2.cumulative_volume_sol - 3.0) < 1e-9


def test_wallet_position_concentration():
    r = WalletStateReducer("W")
    r.apply(_swap(Side.buy, 1.0, 100, 0, mint="A"))
    s = r.apply(_swap(Side.buy, 1.0, 100, 1, mint="B"))
    # two equal positions → Herfindahl = 0.5
    assert abs(s.position_concentration - 0.5) < 1e-9
    assert s.open_positions == 2


def test_wallet_state_is_replay_deterministic():
    swaps = [_swap(Side.buy, 1.0, 100, 0), _swap(Side.sell, 1.5, 100, 5),
             _swap(Side.buy, 2.0, 50, 6)]
    a = [s.model_dump() for s in (WalletStateReducer("W").apply(x) for x in swaps)]
    b = [s.model_dump() for s in (WalletStateReducer("W").apply(x) for x in swaps)]
    assert a == b  # deterministic given the same ordered events


def test_creator_state_evolves():
    r = CreatorStateReducer("C")
    r.on_launch(T0)
    r.on_launch(T0 + timedelta(days=1))
    s = r.on_resolved(T0 + timedelta(days=2), rugged=True, max_multiple=3.0)
    assert s.launches_so_far == 2
    assert s.rugs_so_far == 1
    assert abs(s.rug_rate - 0.5) < 1e-9
    assert s.best_multiple_so_far == 3.0


def test_graph_state_density_and_delta():
    r = GraphStateReducer()
    s1 = r.snapshot(T0, wallets=10, co_buy_edges=5, funded_edges=3, transfer_edges=2, clusters=1)
    assert s1.density == 1.0  # 10 edges / 10 wallets
    s2 = r.snapshot(T0 + timedelta(minutes=1), wallets=10, co_buy_edges=8,
                    funded_edges=3, transfer_edges=2, clusters=1)
    assert s2.new_edges_delta == 3  # 13 - 10


def test_build_trajectory_phase_transitions():
    snaps = [
        TokenSnapshot(mint="M", window=Window.s60, ts=T0, seq=0, age_seconds=0,
                      phase=LifecyclePhase.birth, price_sol=1.0),
        TokenSnapshot(mint="M", window=Window.s60, ts=T0, seq=1, age_seconds=60,
                      phase=LifecyclePhase.growth, price_sol=2.0),
        TokenSnapshot(mint="M", window=Window.s60, ts=T0, seq=2, age_seconds=120,
                      phase=LifecyclePhase.growth, price_sol=3.0),
        TokenSnapshot(mint="M", window=Window.s60, ts=T0, seq=3, age_seconds=180,
                      phase=LifecyclePhase.viral, price_sol=8.0),
    ]
    traj = build_trajectory("M", T0, snaps)
    assert traj.seq_len == 4
    # consecutive duplicates collapsed → birth, growth, viral
    assert traj.phases_seen == ["birth", "growth", "viral"]
