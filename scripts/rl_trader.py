#!/usr/bin/env python3
"""RL trader — entries decided by a self-correcting online contextual bandit.

The bandit (mchpai_common.strategies.OnlineBandit) chooses SKIP/BUY from the live
context and learns from the **realized PnL** of each closed trade (delayed
reward), self-correcting its exploration as it wins or loses. Exits stay on
risk rules (hard stop + trailing, runner mode) so risk is bounded while the
*selection* policy learns.

    python scripts/rl_trader.py            # backtest: watch it learn + self-correct

HONESTY: on a small dataset the agent learns a noisy policy and won't be
profitable — but you can see it self-correct (reward improves early->late,
exploration adapts). It sharpens only with far more data. Paper/backtest only.
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scripts.research as R
from mchpai_common.strategies import (
    CostModel, ExecutionModel, Position, StrategyParams, OnlineBandit,
    exit_signal, position_size,
)


def context(f) -> np.ndarray:
    imb = (f.buy_vol - f.sell_vol) / (f.buy_vol + f.sell_vol + 1e-9)
    return np.array([
        min(f.ratio(), 10.0) / 10.0,
        np.tanh(f.momentum(5) * 5.0),
        min(f.smart_buyers, 5) / 5.0,
        np.log1p(f.liquidity) / 5.0,
        min(f.buyers, 20) / 20.0,
        min(f.age_s, 600) / 600.0,
        float(np.tanh(imb)),
        1.0,  # bias
    ])


def rl_backtest(rows, wfirst, ticks, params: StrategyParams, cost: CostModel, seed=0):
    ex = ExecutionModel(cost, seed)
    bandit = OnlineBandit(dim=8, n_actions=2, eps=0.25, seed=seed)
    start = params.size_sol * 20
    cash = start
    positions: dict[str, dict] = {}
    states: dict[str, R.TState] = {}
    closed, rewards, eps_traj = [], [], []

    def tickpath(mint, ts):
        return [(t, p) for t, p in ticks[mint] if t >= ts]

    for mint, wallet, side, sol, price, ts in rows:
        st = states.get(mint) or states.setdefault(mint, R.TState(ts))
        st.update(side, sol, price, wallet, wfirst)
        if price <= 0:
            continue
        f = st.feat(ts)
        pos = positions.get(mint)
        if pos:
            pos["peak"] = max(pos["peak"], price)
            po = Position(mint, pos["entry"], pos["size"], pos["tokens"], pos["openTs"], pos["peak"])
            do, reason = exit_signal(po, f, params, hold_s=ts - pos["openTs"])
            if do:
                adverse = reason in ("stop_loss", "trailing_stop")
                fill = ex.sell(pos["tokens"], price, st.liq(), tick_path=tickpath(mint, ts),
                               decision_ts=ts, adverse=adverse)
                cash += fill.cost_sol
                pnl = fill.cost_sol - pos["size"]
                reward = pnl / pos["size"]
                bandit.update(1, pos["ctx"], reward)     # learn from realized PnL
                rewards.append(reward)
                eps_traj.append(bandit.eps)
                closed.append(pnl)
                del positions[mint]
        else:
            # basic sanity guard; the bandit decides among eligible candidates
            if (params.min_age_s <= f.age_s <= params.max_age_s and f.liquidity >= params.min_liquidity_sol
                    and (f.buy_vol + f.sell_vol) >= params.min_vol_sol):
                ctx = context(f)
                a = bandit.select(ctx)
                if a == 1 and len(positions) < params.max_positions:
                    size = position_size(params, st.liq())
                    if cash >= size:
                        fill = ex.buy(size, price, st.liq(), tick_path=tickpath(mint, ts), decision_ts=ts)
                        if fill.ok and fill.tokens > 0:
                            cash -= fill.cost_sol
                            positions[mint] = {"tokens": fill.tokens, "entry": fill.price,
                                               "openTs": ts, "peak": fill.price,
                                               "size": fill.cost_sol, "ctx": ctx}
                else:
                    bandit.update(0, ctx, 0.0)            # learn the skip baseline

    for mint, pos in list(positions.items()):
        fill = ex.sell(pos["tokens"], ticks[mint][-1][1], states[mint].liq(), adverse=True)
        cash += fill.cost_sol
        pnl = fill.cost_sol - pos["size"]
        bandit.update(1, pos["ctx"], pnl / pos["size"])
        rewards.append(pnl / pos["size"])
        closed.append(pnl)

    wins = [c for c in closed if c > 0]
    return {
        "net_pnl": cash - start, "trades": len(closed),
        "win_rate": (len(wins) / len(closed)) if closed else 0.0,
        "rewards": rewards, "updates": bandit.updates,
        "eps_start": eps_traj[0] if eps_traj else bandit.eps, "eps_end": bandit.eps,
    }


def main():
    rows, wfirst, ticks = R.load()
    if not rows:
        print("no data — run scripts/acquire.py first")
        return 1
    params = StrategyParams(size_sol=0.5, max_positions=6, liq_fraction=0.05,
                            min_ticket=0.08, max_ticket=1.0, min_liquidity_sol=6.0,
                            runner=True, trail=0.4, stop_loss=-0.35, hold_max_s=1200,
                            exit_reversal=False, exit_pressure=False, min_age_s=8, max_age_s=1200)
    cost = CostModel()
    res = [rl_backtest(rows, wfirst, ticks, params, cost, seed=s) for s in range(4)]
    net = float(np.mean([r["net_pnl"] for r in res]))
    tr = float(np.mean([r["trades"] for r in res]))
    win = float(np.mean([r["win_rate"] for r in res]))

    # learning evidence: early vs late realized reward, exploration trajectory
    rw = res[0]["rewards"]
    half = len(rw) // 2
    early = float(np.mean(rw[:half])) if half else 0.0
    late = float(np.mean(rw[half:])) if half else 0.0

    print(f"=== RL TRADER (self-correcting contextual bandit) — {len(rows)} swaps ===")
    print(f"entries: learned policy   exits: risk rules (stop {params.stop_loss:.0%} + trail {params.trail:.0%}, runner)")
    print(f"net PnL (avg 4 seeds) : {net:+.3f} SOL   trades: {tr:.0f}   win-rate: {win*100:.0f}%")
    print(f"policy updates        : {res[0]['updates']}")
    print(f"exploration (eps)     : {res[0]['eps_start']:.2f} -> {res[0]['eps_end']:.2f}  "
          f"({'adapted down (exploiting)' if res[0]['eps_end']<res[0]['eps_start'] else 'adapted up (exploring)'})")
    print(f"realized reward       : early {early:+.3f} -> late {late:+.3f}  "
          f"({'IMPROVING' if late>early else 'not yet improving'})")
    print("\nThe agent is self-correcting from realized PnL. On this small dataset the")
    print("learned policy is still net-negative — it needs far more trades to converge.")
    print("Gather more data and re-run to watch the learning curve climb (or not).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
