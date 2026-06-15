#!/usr/bin/env python3
"""Full-suite real-data backtest: run EVERY entry archetype the dashboard uses
over the real collected swaps and report SOL/hour for each.

My earlier real-data test only ran the 'alpha' gate (which missed every runner).
The system also runs tiered-newborn, trending, momentum, and signal entries — a
different archetype may catch what alpha missed. This evaluates all of them on
the same real swaps with the realistic execution model (fills at actual forward
prices) and the moonbag/scale-out exit, and reports the honest per-strategy
SOL/hr + whether each caught a real runner.

    python scripts/realtest_suite.py
"""
from __future__ import annotations

import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scripts.research as R
from mchpai_common.strategies import CostModel, ExecutionModel

MOON = dict(sl=-0.25, scaleAt=0.6, scaleFrac=0.5, moonAt=1.5,
            moonFrac=0.25, moonTrail=0.55, hold_max_s=1800)


def entry_ok(kind, st, f, side, sol):
    b = f.buyers
    age = f.age_s
    if not (f.liquidity >= 2 and f.price > 0):
        return False
    if kind == "alpha":
        return age >= 8 and b >= 5 and bool(st.smart) and f.ratio() >= 1.5 and f.momentum(5) > 0
    if kind == "tiered":
        if st.sell_vol > max(2, b * 0.25):
            return False
        return (age <= 60 and b >= 8) or (age <= 120 and b >= 20) or (age <= 180 and b >= 60)
    if kind == "trending":
        return age >= 5 and (b / max(age, 1) * 60) >= 6 and f.ratio() >= 1.0
    if kind == "momentum":
        return age >= 8 and b >= 4 and f.ratio() >= 2.0 and f.momentum(5) >= 0.03
    if kind == "signal":
        # whale buy / breakout / smart-wallet present
        return (side == "buy" and sol >= 3) or bool(st.smart) or f.momentum(5) >= 0.05
    return False


def run(kind, seed=0, size=0.5):
    rows, wfirst, ticks = R.load()
    if not rows:
        return None
    ex = ExecutionModel(CostModel(), seed)
    span = (rows[-1][5] - rows[0][5]) or 1
    states, positions, closed = {}, {}, []
    cash = start = 20.0
    best = 0.0

    def tp(mint, ts):
        return [(t, p) for t, p in ticks[mint] if t >= ts]

    for mint, wallet, side, sol, price, ts in rows:
        st = states.get(mint) or states.setdefault(mint, R.TState(ts))
        st.update(side, sol, price, wallet, wfirst)
        if price <= 0:
            continue
        f = st.feat(ts)
        pos = positions.get(mint)
        if pos:
            p_ = price
            pos["peak"] = max(pos["peak"], p_)
            ret = p_ / pos["entry"] - 1
            done = reason = None
            if not pos["scaled"] and ret <= MOON["sl"]:
                done, reason = True, "stop"
            elif not pos["scaled"] and ret >= MOON["scaleAt"]:
                fl = ex.sell(pos["tokens"] * MOON["scaleFrac"], p_, st.liq(), tick_path=tp(mint, ts), decision_ts=ts)
                cash += fl.cost_sol
                closed.append(fl.cost_sol - pos["cost"] * MOON["scaleFrac"])
                pos["tokens"] *= (1 - MOON["scaleFrac"]); pos["cost"] *= (1 - MOON["scaleFrac"])
                pos["scaled"], pos["floor"] = True, pos["entry"]
            elif pos["scaled"]:
                if not pos["mooned"] and ret >= MOON["moonAt"]:
                    rem = 1 - MOON["scaleFrac"]
                    sf = (1 - MOON["moonFrac"] / rem) if rem > MOON["moonFrac"] else 0
                    if sf > 0:
                        fl = ex.sell(pos["tokens"] * sf, p_, st.liq(), tick_path=tp(mint, ts), decision_ts=ts)
                        cash += fl.cost_sol; closed.append(fl.cost_sol - pos["cost"] * sf)
                        pos["tokens"] *= (1 - sf); pos["cost"] *= (1 - sf)
                    pos["mooned"] = True
                if not pos["mooned"] and p_ <= pos["floor"]:
                    done, reason = True, "breakeven"
                elif pos["mooned"] and p_ <= pos["peak"] * (1 - MOON["moonTrail"]):
                    done, reason = True, "moonbag"
            if not done and (ts - pos["openTs"]) >= MOON["hold_max_s"]:
                done, reason = True, "timeout"
            if done:
                fl = ex.sell(pos["tokens"], p_, st.liq(), tick_path=tp(mint, ts), decision_ts=ts,
                             adverse=reason in ("stop", "breakeven"))
                cash += fl.cost_sol
                pnl = fl.cost_sol - pos["cost"]
                closed.append(pnl)
                best = max(best, (p_ / pos["entry"]))
                del positions[mint]
        elif len(positions) < 6 and cash >= size and entry_ok(kind, st, f, side, sol):
            fl = ex.buy(size, price, st.liq(), tick_path=tp(mint, ts), decision_ts=ts)
            if fl.ok and fl.tokens > 0:
                cash -= fl.cost_sol
                positions[mint] = dict(tokens=fl.tokens, entry=fl.price, cost=fl.cost_sol,
                                       openTs=ts, peak=fl.price, scaled=False, mooned=False, floor=0.0)
    for mint, pos in list(positions.items()):
        fl = ex.sell(pos["tokens"], ticks[mint][-1][1], states[mint].liq(), adverse=True)
        cash += fl.cost_sol; closed.append(fl.cost_sol - pos["cost"])
    net = cash - start
    return dict(kind=kind, net=net, trades=len(closed), per_hr=net / (span / 3600),
                win=sum(1 for c in closed if c > 0), best_mult=best, span_h=span / 3600)


def main():
    kinds = ["alpha", "tiered", "trending", "momentum", "signal"]
    span = None
    print("=== FULL-SUITE real-data backtest (avg 4 seeds, realistic costs) ===")
    print(f"{'entry':>10}{'SOL/hr':>9}{'net◎':>8}{'trades':>8}{'win':>5}{'bestX':>7}")
    results = []
    for k in kinds:
        rs = [run(k, s) for s in range(4)]
        rs = [r for r in rs if r]
        if not rs:
            print("no data"); return 1
        span = rs[0]["span_h"]
        m = {key: statistics.mean(r[key] for r in rs) for key in ("net", "trades", "per_hr", "win", "best_mult")}
        results.append((k, m))
        print(f"{k:>10}{m['per_hr']:>+9.2f}{m['net']:>+8.2f}{m['trades']:>8.0f}{m['win']:>5.0f}{m['best_mult']:>6.1f}x")
    best = max(results, key=lambda kv: kv[1]["per_hr"])
    print(f"\nspan: {span:.2f}h · target 5-10 SOL/hr")
    print("--- honest verdict ---")
    if best[1]["per_hr"] >= 5:
        print(f"'{best[0]}' clears the target on THIS data ({best[1]['per_hr']:+.2f}/hr) — but on a "
              f"{span:.1f}h sample with few runners this is NOT trustworthy (one token can flatter it).")
    else:
        print(f"No archetype clears 5-10 SOL/hr on this data (best '{best[0]}' {best[1]['per_hr']:+.2f}/hr).")
        print(f"The {span:.1f}h sample is too thin (≈1 real 10x) to realize the fat-tail edge; this is an")
        print("honest negative across the WHOLE suite. Needs many hours of broad real data to validate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
