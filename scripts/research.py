#!/usr/bin/env python3
"""MCHPAI strategy research — realistic backtest + parameter search.

Replays the collected swaps through the strategy under the **realistic execution
model** (latency, slippage/price-impact, fees, failure probability) and searches a
parameter grid for a configuration that actually survives costs. Reports net PnL,
win rate, profit factor, Sharpe, and max drawdown — and tells the truth about
whether any edge exists in the data.

The "unique" lever is ``smart_min``: gate entries on **experienced wallets**
(seen before this token) buying early — the platform's wallet intelligence — vs.
naive momentum. The search shows whether that gating helps.

    python scripts/research.py
    python scripts/research.py --quick     # smaller grid

HONESTY: small/young data + optimistic-but-not-perfect fills. A positive result
here is a hypothesis, not a guarantee; a negative result is a real finding.
"""

from __future__ import annotations

import argparse
import itertools
import os
import sqlite3
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mchpai_common.strategies import (
    CostModel, ExecutionModel, Features, Position, StrategyParams,
    entry_signal, exit_signal,
)

ACQ_DB = os.environ.get("ACQUIRE_DB", "data/acquisition.db")


def load():
    conn = sqlite3.connect(f"file:{ACQ_DB}?mode=ro", uri=True)
    rows = conn.execute("SELECT mint, wallet, side, sol_amount, price, ts FROM swaps "
                        "WHERE price IS NOT NULL ORDER BY ts, slot").fetchall()
    wfirst = {w: t for w, t in conn.execute("SELECT wallet, min(ts) FROM swaps GROUP BY wallet")}
    conn.close()
    ticks = defaultdict(list)
    for mint, _w, _s, _sol, price, ts in rows:
        ticks[mint].append((ts, price))
    return rows, wfirst, ticks


class TState:
    __slots__ = ("birth", "last", "buy_vol", "sell_vol", "buyers", "smart", "prices", "cumvol")

    def __init__(self, ts):
        self.birth = ts
        self.last = 0.0
        self.buy_vol = self.sell_vol = self.cumvol = 0.0
        self.buyers = set()
        self.smart = set()
        self.prices = []

    def update(self, side, sol, price, wallet, wfirst):
        self.cumvol += sol
        if price:
            self.last = price
            self.prices.append(price)
            if len(self.prices) > 30:
                self.prices.pop(0)
        if side == "buy":
            self.buy_vol += sol
            self.buyers.add(wallet)
            if wfirst.get(wallet, self.birth) < self.birth:
                self.smart.add(wallet)
        else:
            self.sell_vol += sol

    def feat(self, ts):
        return Features(price=self.last, buy_vol=self.buy_vol, sell_vol=self.sell_vol,
                        buyers=len(self.buyers), age_s=ts - self.birth,
                        prices=list(self.prices), smart_buyers=len(self.smart))

    def liq(self):
        return max(self.cumvol, 5.0)


def backtest(rows, wfirst, ticks, params: StrategyParams, cost: CostModel, seed=0):
    ex = ExecutionModel(cost, seed)
    start = params.size_sol * 20
    cash = start
    positions: dict[str, dict] = {}
    states: dict[str, TState] = {}
    closed: list[float] = []   # per-trade PnL (SOL)
    rets: list[float] = []     # per-trade return
    eq_curve = [start]
    slips = []

    def tickpath(mint, ts):
        return [(t, p) for t, p in ticks[mint] if t >= ts]

    for mint, wallet, side, sol, price, ts in rows:
        st = states.get(mint) or states.setdefault(mint, TState(ts))
        st.update(side, sol, price, wallet, wfirst)
        if price <= 0:
            continue
        f = st.feat(ts)
        pos = positions.get(mint)
        if pos:
            pos["peak"] = max(pos["peak"], price)
            po = Position(mint, pos["entry"], params.size_sol, pos["tokens"], pos["openTs"], pos["peak"])
            do, reason = exit_signal(po, f, params, hold_s=ts - pos["openTs"])
            if do:
                adverse = reason in ("stop_loss", "trailing_stop", "momentum_reversal", "sell_pressure")
                fill = ex.sell(pos["tokens"], price, st.liq(), tick_path=tickpath(mint, ts),
                               decision_ts=ts, adverse=adverse)
                cash += fill.cost_sol
                pnl = fill.cost_sol - pos["size"]
                closed.append(pnl)
                rets.append(pnl / pos["size"])
                slips.append(fill.slippage_bps)
                eq_curve.append(cash + sum(p["tokens"] * states[m].last for m, p in positions.items() if m != mint))
                del positions[mint]
        elif len(positions) < params.max_positions and cash >= params.size_sol:
            if entry_signal(f, params):
                fill = ex.buy(params.size_sol, price, st.liq(), tick_path=tickpath(mint, ts), decision_ts=ts)
                if fill.ok and fill.tokens > 0:
                    cash -= fill.cost_sol
                    slips.append(fill.slippage_bps)
                    positions[mint] = {"tokens": fill.tokens, "entry": fill.price,
                                       "openTs": ts, "peak": fill.price, "size": fill.cost_sol}

    # liquidate stragglers at last price (adverse)
    for mint, pos in list(positions.items()):
        lastp = ticks[mint][-1][1]
        fill = ex.sell(pos["tokens"], lastp, states[mint].liq(), adverse=True)
        cash += fill.cost_sol
        pnl = fill.cost_sol - pos["size"]
        closed.append(pnl)
        rets.append(pnl / pos["size"])

    net = cash - start
    wins = [c for c in closed if c > 0]
    losses = [c for c in closed if c < 0]
    arr = np.array(rets) if rets else np.array([0.0])
    eq = np.array(eq_curve)
    dd = float(((np.maximum.accumulate(eq) - eq) / np.maximum.accumulate(eq)).max()) if len(eq) > 1 else 0.0
    return {
        "net_pnl": net, "ret_pct": net / start * 100, "trades": len(closed),
        "win_rate": (len(wins) / len(closed)) if closed else 0.0,
        "profit_factor": (sum(wins) / abs(sum(losses))) if losses else (float("inf") if wins else 0.0),
        "sharpe": float(arr.mean() / (arr.std() + 1e-9)),
        "max_dd_pct": dd * 100,
        "avg_slip_bps": float(np.mean(slips)) if slips else 0.0,
    }


def search(quick=False):
    rows, wfirst, ticks = load()
    if not rows:
        print("no data — run scripts/acquire.py first")
        return
    grid = {
        "ratio_in": [1.5, 2.5] if quick else [1.5, 2.5, 4.0],
        "take_profit": [0.4, 0.8] if quick else [0.3, 0.6, 1.0],
        "stop_loss": [-0.25] if quick else [-0.3, -0.2],
        "smart_min": [0, 1, 2],
        "mom_in": [0.05] if quick else [0.03, 0.1],
    }
    cost = CostModel()
    keys = list(grid)
    results = []
    for combo in itertools.product(*[grid[k] for k in keys]):
        kw = dict(zip(keys, combo))
        p = StrategyParams(size_sol=0.5, max_positions=5, **kw)
        # average a few seeds (failure prob is stochastic)
        ms = [backtest(rows, wfirst, ticks, p, cost, seed=s) for s in range(3)]
        m = {k: float(np.mean([x[k] for x in ms])) for k in ms[0]}
        m["params"] = kw
        results.append(m)

    elig = [r for r in results if r["trades"] >= 8]
    elig.sort(key=lambda r: -r["net_pnl"])
    print(f"=== REALISTIC STRATEGY SEARCH ({len(rows)} swaps, {len(results)} configs) ===")
    print("cost model: latency ~1.25s, slippage = 80bps + impact, 1% fee/side, "
          "0.0018◎ fixed, 12% fail")
    print(f"\n{'net◎':>7}{'ret%':>7}{'trades':>7}{'win%':>6}{'PF':>6}{'sharpe':>7}{'maxDD%':>7}  params")
    for r in (elig[:8] or sorted(results, key=lambda r: -r["net_pnl"])[:8]):
        print(f"{r['net_pnl']:>7.2f}{r['ret_pct']:>7.1f}{r['trades']:>7.0f}{r['win_rate']*100:>6.0f}"
              f"{min(r['profit_factor'],9.99):>6.2f}{r['sharpe']:>7.2f}{r['max_dd_pct']:>7.1f}  "
              f"ratio>={r['params']['ratio_in']} tp+{r['params']['take_profit']:.0%} "
              f"sl{r['params']['stop_loss']:.0%} smart>={r['params']['smart_min']} mom+{r['params']['mom_in']:.0%}")

    best = elig[0] if elig else None
    print("\n--- verdict ---")
    if best and best["net_pnl"] > 0 and best["win_rate"] >= 0.5:
        print(f"Best config is NET POSITIVE after realistic costs: {best['net_pnl']:+.2f}◎ "
              f"({best['ret_pct']:+.0f}%), win {best['win_rate']*100:.0f}%, {best['trades']:.0f} trades.")
        print("⚠ Small sample — this is a HYPOTHESIS to validate on far more data, not a proven edge.")
    else:
        print("No config is convincingly positive after realistic costs on this data.")
        print("That is the honest result: edge is unproven. Gather more data and re-run;")
        print("do NOT trade live on this.")
    # did smart-money gating help?
    by_smart = defaultdict(list)
    for r in results:
        by_smart[r["params"]["smart_min"]].append(r["net_pnl"])
    print("\nsmart-money gating (avg net◎ across configs):")
    for sm in sorted(by_smart):
        print(f"  smart_min={sm}: {np.mean(by_smart[sm]):+.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    search(quick=args.quick)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
