#!/usr/bin/env python3
"""Real-data read of the CURRENT engine (alpha gate + moonbag exit).

Runs the dashboard's current strategy — confluence-ish entry + scale-out/moonbag
exit — over the REAL collected swaps in data/acquisition.db, with fills at the
ACTUAL forward prices (the execution model walks each token's real tick path).
Reports net SOL, trade count, and realized SOL/hour over the real span.

This is the honest real-data answer to "is it making 5-10 SOL/hr?" — whatever it
is. A tiny sample (a single short window) cannot contain the rare fat-tail
winners the strategy depends on, so a flat/negative read here is expected and is
NOT proof the approach can't work — only that THIS data doesn't show it.

    python scripts/realtest.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scripts.research as R
from mchpai_common.strategies import CostModel, ExecutionModel

MOON = dict(sl=-0.25, scaleAt=0.6, scaleFrac=0.5, moonAt=1.5,
            moonFrac=0.25, moonTrail=0.55, hold_max_s=1800)


def run(seed: int = 0):
    rows, wfirst, ticks = R.load()
    if not rows:
        print("no data — data/acquisition.db empty")
        return None
    ex = ExecutionModel(CostModel(), seed)
    span = (rows[-1][5] - rows[0][5]) or 1
    states: dict[str, R.TState] = {}
    cash = 20.0
    start = cash
    positions: dict[str, dict] = {}
    closed: list[float] = []
    size = 0.5

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
            p_ = price
            pos["peak"] = max(pos["peak"], p_)
            ret = p_ / pos["entry"] - 1
            done = reason = None
            if not pos["scaled"] and ret <= MOON["sl"]:
                done, reason = True, "stop"
            elif not pos["scaled"] and ret >= MOON["scaleAt"]:
                # scale out cost, set breakeven
                fill = ex.sell(pos["tokens"] * MOON["scaleFrac"], p_, st.liq(),
                               tick_path=tickpath(mint, ts), decision_ts=ts)
                cash += fill.cost_sol
                closed.append(fill.cost_sol - pos["cost"] * MOON["scaleFrac"])
                pos["tokens"] *= (1 - MOON["scaleFrac"])
                pos["cost"] *= (1 - MOON["scaleFrac"])
                pos["scaled"], pos["floor"] = True, pos["entry"]
            elif pos["scaled"]:
                if not pos["mooned"] and ret >= MOON["moonAt"]:
                    rem = 1 - MOON["scaleFrac"]
                    sellf = (1 - MOON["moonFrac"] / rem) if rem > MOON["moonFrac"] else 0
                    if sellf > 0:
                        fill = ex.sell(pos["tokens"] * sellf, p_, st.liq(),
                                       tick_path=tickpath(mint, ts), decision_ts=ts)
                        cash += fill.cost_sol
                        closed.append(fill.cost_sol - pos["cost"] * sellf)
                        pos["tokens"] *= (1 - sellf)
                        pos["cost"] *= (1 - sellf)
                    pos["mooned"] = True
                if not pos["mooned"] and p_ <= pos["floor"]:
                    done, reason = True, "breakeven"
                elif pos["mooned"] and p_ <= pos["peak"] * (1 - MOON["moonTrail"]):
                    done, reason = True, "moonbag"
            if not done and (ts - pos["openTs"]) >= MOON["hold_max_s"]:
                done, reason = True, "timeout"
            if done:
                fill = ex.sell(pos["tokens"], p_, st.liq(), tick_path=tickpath(mint, ts),
                               decision_ts=ts, adverse=reason in ("stop", "breakeven"))
                cash += fill.cost_sol
                closed.append(fill.cost_sol - pos["cost"])
                del positions[mint]
        else:
            # alpha-ish entry gate (confluence proxy on real features)
            if (len(positions) < 6 and cash >= size and f.age_s >= 8
                    and f.buyers >= 5 and f.liquidity >= 3
                    and st.smart and f.ratio() >= 1.5 and f.momentum(5) > 0):
                fill = ex.buy(size, price, st.liq(), tick_path=tickpath(mint, ts), decision_ts=ts)
                if fill.ok and fill.tokens > 0:
                    cash -= fill.cost_sol
                    positions[mint] = {"tokens": fill.tokens, "entry": fill.price,
                                       "cost": fill.cost_sol, "openTs": ts, "peak": fill.price,
                                       "scaled": False, "mooned": False, "floor": 0.0}

    for mint, pos in list(positions.items()):
        lastp = ticks[mint][-1][1]
        fill = ex.sell(pos["tokens"], lastp, states[mint].liq(), adverse=True)
        cash += fill.cost_sol
        closed.append(fill.cost_sol - pos["cost"])

    net = cash - start
    wins = [c for c in closed if c > 0]
    return dict(net=net, trades=len(closed), wins=len(wins), span_h=span / 3600,
                per_hr=net / (span / 3600))


def main():
    res = [run(s) for s in range(4)]
    res = [r for r in res if r]
    if not res:
        return 1
    import statistics
    net = statistics.mean(r["net"] for r in res)
    per = statistics.mean(r["per_hr"] for r in res)
    tr = statistics.mean(r["trades"] for r in res)
    span = res[0]["span_h"]
    print(f"=== REAL-DATA moonbag/alpha read · {span:.2f}h of collected swaps · avg 4 seeds ===")
    print(f"net PnL    : {net:+.3f} SOL over {span:.2f}h")
    print(f"SOL/hour   : {per:+.2f}   (target 5-10)")
    print(f"trades     : {tr:.0f}   (fat-tail payoff needs FAR more to realize)")
    print("\n--- honest verdict ---")
    if per >= 5:
        print(f"Clears the target on THIS data ({per:+.2f}/hr) — but a {span:.1f}h sample is")
        print("far too small to trust; one lucky runner can flatter it. Not proof.")
    else:
        print(f"Does NOT clear 5-10 SOL/hr on this data ({per:+.2f}/hr). Expected: a short,")
        print("narrow (pump.fun-only) sample with few qualifying entries cannot contain the")
        print("rare ~2% moonshots that drive the edge. Real capability needs many hours of")
        print("full-firehose data — gather it (dashboard IndexedDB / server ingestor) and")
        print("re-run the backtester. This is an honest negative, not a hidden one.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
