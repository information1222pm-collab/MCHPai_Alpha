"""Tests for the realistic execution model (latency, slippage, fees, failures)."""

from mchpai_common.strategies import CostModel, ExecutionModel


def test_buy_fills_worse_than_intended():
    ex = ExecutionModel(CostModel(fail_prob=0.0), seed=1)
    fill = ex.buy(size_sol=0.5, intended_price=1.0, liq_sol=100.0)
    assert fill.ok
    assert fill.price > 1.0           # you buy higher than you saw (slippage+drift)
    assert fill.fee_sol > 0
    assert fill.tokens < 0.5 / 1.0    # fewer tokens than naive


def test_sell_fills_worse_than_intended():
    ex = ExecutionModel(CostModel(fail_prob=0.0), seed=1)
    fill = ex.sell(tokens=1000.0, intended_price=1.0, liq_sol=100.0)
    assert fill.ok
    assert fill.price < 1.0           # you sell lower than you saw


def test_impact_scales_with_size_vs_liquidity():
    c = CostModel(fail_prob=0.0)
    ex = ExecutionModel(c, seed=1)
    small = ex.buy(0.1, 1.0, liq_sol=1000.0)
    big = ex.buy(5.0, 1.0, liq_sol=10.0)   # large order into thin liquidity
    assert big.slippage_bps > small.slippage_bps


def test_failures_happen():
    ex = ExecutionModel(CostModel(fail_prob=1.0), seed=1)
    assert ex.buy(0.5, 1.0, 100.0).ok is False   # always fails when p=1


def test_latency_uses_forward_path():
    # price rises after the decision; with latency we fill at the higher later price
    ex = ExecutionModel(CostModel(fail_prob=0.0, base_slippage_bps=0, impact_k=0,
                                  fee_bps=0, fixed_cost_sol=0), seed=1)
    path = [(0.0, 1.0), (1.0, 1.2), (2.0, 1.5)]   # ts, price
    fill = ex.buy(0.5, intended_price=1.0, liq_sol=1e9, tick_path=path, decision_ts=0.0)
    assert fill.price >= 1.2          # landed ~1.25s later, not at 1.0


def test_adverse_exit_costs_more():
    ex = ExecutionModel(CostModel(fail_prob=0.0), seed=1)
    normal = ex.sell(1000.0, 1.0, 100.0, adverse=False)
    gap = ex.sell(1000.0, 1.0, 100.0, adverse=True)
    assert gap.price < normal.price   # stopping into a dump fills worse
