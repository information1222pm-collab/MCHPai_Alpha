"""Tests for windowed snapshot aggregation + lifecycle labeling."""

from datetime import datetime, timezone

from mchpai_common.schemas.common import Side
from mchpai_common.schemas.snapshot import LifecyclePhase, Window
from mchpai_common.schemas.swap import Dex, SwapEvent
from mchpai_common.snapshots import WindowAggregator, label_sequence

BASE = 1_000_000  # epoch seconds, divisible by 5 → clean bucket boundaries
MINT = "M"


def _swap(offset, side, sol, tok, price):
    return SwapEvent(
        signature=f"s{offset}", slot=offset,
        timestamp=datetime.fromtimestamp(BASE + offset, tz=timezone.utc),
        dex=Dex.unknown, wallet_address=f"w{offset}", token_address=MINT,
        side=side, sol_amount=sol, token_amount=tok, price=price,
    )


def test_bucket_closes_and_aggregates():
    birth = datetime.fromtimestamp(BASE, tz=timezone.utc)
    agg = WindowAggregator(MINT, Window.s5, birth)

    # bucket 0: offsets 0,1,2 ; a swap at offset 6 (bucket 1) closes bucket 0
    out = []
    out += agg.add(_swap(0, Side.buy, 1.0, 100, 0.01))
    out += agg.add(_swap(1, Side.buy, 2.0, 100, 0.02))
    out += agg.add(_swap(2, Side.sell, 0.5, 50, 0.015))
    assert out == []  # nothing closed yet
    out += agg.add(_swap(6, Side.buy, 1.0, 10, 0.03))

    assert len(out) == 1
    snap = out[0]
    assert snap.seq == 0
    assert snap.window == Window.s5
    assert snap.txns == 3
    assert snap.buyers == 2 and snap.sellers == 1
    assert abs(snap.volume_sol - 3.5) < 1e-9
    assert snap.open_sol == 0.01 and snap.close_sol == 0.015
    assert snap.high_sol == 0.02 and snap.low_sol == 0.01
    assert abs(snap.net_flow_sol - (3.0 - 0.5)) < 1e-9


def test_flush_closes_inflight_bucket():
    birth = datetime.fromtimestamp(BASE, tz=timezone.utc)
    agg = WindowAggregator(MINT, Window.s15, birth)
    agg.add(_swap(0, Side.buy, 1.0, 100, 0.01))
    flushed = agg.flush()
    assert len(flushed) == 1 and flushed[0].txns == 1


def test_smart_money_ratio_with_alpha_lookup():
    birth = datetime.fromtimestamp(BASE, tz=timezone.utc)
    alpha = {"w0": 90.0, "w1": 10.0}
    agg = WindowAggregator(MINT, Window.s5, birth, alpha_lookup=lambda a: alpha.get(a, 0.0))
    agg.add(_swap(0, Side.buy, 3.0, 100, 0.01))   # smart (alpha 90)
    agg.add(_swap(1, Side.buy, 1.0, 100, 0.01))   # not smart
    # the offset-6 swap lands in the next bucket and closes bucket 0 (offsets 0,1)
    snap = agg.add(_swap(6, Side.buy, 1.0, 10, 0.02))[0]
    assert abs(snap.smart_money_ratio - 0.75) < 1e-9  # 3.0 smart of 4.0 SOL volume


def test_lifecycle_labeling_orders_phases():
    from mchpai_common.schemas.snapshot import TokenSnapshot

    seq = [
        TokenSnapshot(mint=MINT, window=Window.s60, ts=datetime.now(timezone.utc),
                      seq=0, age_seconds=10, txns=2, net_flow_sol=0.1, liquidity_sol=5),
        TokenSnapshot(mint=MINT, window=Window.s60, ts=datetime.now(timezone.utc),
                      seq=1, age_seconds=300, txns=50, net_flow_sol=5, r0=2.0,
                      volume_sol=10, liquidity_sol=50),
        TokenSnapshot(mint=MINT, window=Window.s60, ts=datetime.now(timezone.utc),
                      seq=2, age_seconds=900, txns=40, net_flow_sol=-8, volume_sol=10,
                      liquidity_sol=40),
    ]
    labeled = label_sequence(seq)
    assert labeled[0].phase == LifecyclePhase.birth
    assert labeled[1].phase == LifecyclePhase.viral
    assert labeled[2].phase == LifecyclePhase.distribution
