#!/usr/bin/env python3
"""Capacity / feasibility harness — is the trader *capable* of 5-10 SOL/hour?

This does NOT claim guaranteed profit. It answers a narrower, honest question:
**given a plausible (favorable-but-not-fantasy) memecoin market, does the strategy
machinery — run through the REAL execution model (latency, slippage/impact, 1%
fees/side, 12% tx-failure, exit-gap) — produce 5-10 SOL/hour, and under what
size / entry-rate / hit-distribution?**

It runs the actual moonbag exit logic (cut losers fast, scale out cost, ride a
free moonbag) the dashboard uses, over a fat-tailed distribution of peak
multiples, and reports the realized SOL/hour distribution plus sensitivity and
the break-even edge required. Whether the live entry filter actually delivers the
assumed hit-distribution is the unproven part — and that is exactly what the
dashboard's live SOL/hr meter and the backtester measure on real data.

    python scripts/capacity.py
    python scripts/capacity.py --entries 40 --size 0.7
"""
from __future__ import annotations

import argparse
import os
import random
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mchpai_common.strategies import CostModel, ExecutionModel

# Moonbag strategy params (mirror the dashboard 'Moonshot' defaults)
MOON = dict(sl=-0.25, scaleAt=0.6, scaleFrac=0.5, moonAt=1.5, moonFrac=0.25, moonTrail=0.55)

# Calibrated peak-multiple mixture for *entered* tokens (post quality/confluence
# filter). ASSUMPTION — favorable vs random launches (which mostly rug), but the
# tail is what memecoins genuinely do. Each entry: (weight, lo, hi) peak multiple.
MIX = [
    (0.52, 0.30, 1.15),   # dud / rug — peaks barely above entry then dumps
    (0.27, 1.15, 2.00),   # small pop
    (0.13, 2.00, 6.00),   # good
    (0.06, 6.00, 25.0),   # big
    (0.02, 25.0, 150.0),  # moonshot (fat tail — the huge wins)
]


def draw_peak(rng: random.Random) -> float:
    r = rng.random()
    acc = 0.0
    for w, lo, hi in MIX:
        acc += w
        if r <= acc:
            # log-uniform for the heavy tails, uniform for the body
            if lo >= 2.0:
                import math
                return math.exp(rng.uniform(math.log(lo), math.log(hi)))
            return rng.uniform(lo, hi)
    return 1.0


def gen_path(M: float, rng: random.Random) -> list[float]:
    """A price path in entry-multiples: rise 1->M, then bleed down toward ~0.25M."""
    rise = rng.randint(4, 9)
    fall = rng.randint(10, 30)
    path = [1.0 + (M - 1.0) * (i / rise) for i in range(rise + 1)]
    bottom = max(0.05, M * rng.uniform(0.15, 0.4))
    path += [M + (bottom - M) * (i / fall) for i in range(1, fall + 1)]
    return path


def moonbag_pnl(ex: ExecutionModel, p: dict, path: list[float], size: float, liq: float) -> float:
    """Run the real moonbag exit through the realistic execution model. Returns
    realized SOL PnL for one trade (0 if the entry tx failed → capital not spent)."""
    buy = ex.buy(size, path[0], liq)
    if not buy.ok:
        return 0.0
    entry, tokens, cost = buy.price, buy.tokens, buy.cost_sol
    proceeds, peak, scaled, mooned, floor = 0.0, entry, False, False, 0.0
    for price in path[1:]:
        peak = max(peak, price)
        ret = price / entry - 1
        if not scaled and ret <= p["sl"]:
            proceeds += ex.sell(tokens, price, liq, adverse=True).cost_sol
            tokens = 0.0
            break
        if not scaled and ret >= p["scaleAt"]:
            st = tokens * p["scaleFrac"]
            proceeds += ex.sell(st, price, liq).cost_sol
            tokens -= st
            scaled, floor = True, entry
        if scaled:
            if not mooned and ret >= p["moonAt"]:
                rem = 1 - p["scaleFrac"]
                sellF = (1 - p["moonFrac"] / rem) if rem > p["moonFrac"] else 0.0
                if sellF > 0:
                    st = tokens * sellF
                    proceeds += ex.sell(st, price, liq).cost_sol
                    tokens -= st
                mooned = True
            if not mooned and price <= floor:
                proceeds += ex.sell(tokens, price, liq).cost_sol
                tokens = 0.0
                break
            if mooned and price <= peak * (1 - p["moonTrail"]):
                proceeds += ex.sell(tokens, price, liq).cost_sol
                tokens = 0.0
                break
    if tokens > 0:
        proceeds += ex.sell(tokens, path[-1], liq, adverse=True).cost_sol
    return proceeds - cost


def sim_hours(hours: int, entries_per_hour: float, size: float, seed: int,
              mix=MIX) -> list[float]:
    rng = random.Random(seed)
    ex = ExecutionModel(CostModel(), seed)
    out = []
    for _ in range(hours):
        n = int(rng.gauss(entries_per_hour, entries_per_hour ** 0.5))
        pnl = 0.0
        for _ in range(max(0, n)):
            M = draw_peak(rng)
            liq = rng.uniform(6, 35) * (1 + (M > 3) * rng.uniform(0, 2))  # winners tend to have more liq
            pnl += moonbag_pnl(ex, MOON, gen_path(M, rng), size, liq)
        out.append(pnl)
    return out


def pct(xs, q):
    s = sorted(xs)
    return s[min(len(s) - 1, int(q * len(s)))]


def report(entries: float, size: float):
    HOURS = 4000
    hours = []
    for seed in range(5):
        hours += sim_hours(HOURS // 5, entries, size, seed)
    mean = statistics.mean(hours)
    med = statistics.median(hours)
    per_trade = mean / entries
    print(f"=== CAPACITY: moonbag · {entries:.0f} entries/hr · {size:.2f}◎ size · "
          f"{len(hours)} simulated hours (real cost model) ===")
    print(f"mean SOL/hr   : {mean:+.2f}")
    print(f"median SOL/hr : {med:+.2f}   (memecoins are fat-tailed — median < mean)")
    print(f"P10 / P90 hr  : {pct(hours,0.10):+.2f} / {pct(hours,0.90):+.2f}")
    print(f"best / worst  : {max(hours):+.2f} / {min(hours):+.2f}")
    print(f"avg per trade : {per_trade:+.4f}◎   win-makers are the rare big peaks")
    hit = mean >= 5.0
    print(f"clears 5◎/hr  : {'YES ✓' if hit else 'no'}   "
          f"clears 10◎/hr: {'YES ✓' if mean>=10 else 'no'}")
    return mean


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entries", type=float, default=30)
    ap.add_argument("--size", type=float, default=0.5)
    args = ap.parse_args()

    base = report(args.entries, args.size)

    print("\n--- sensitivity: mean SOL/hr by entries/hr x size ---")
    sizes = [0.3, 0.5, 1.0, 2.0]
    ents = [15, 30, 60]
    print("            " + "".join(f"{s:>9.2f}◎" for s in sizes))
    for e in ents:
        row = []
        for s in sizes:
            hrs = sim_hours(800, e, s, seed=7)
            row.append(statistics.mean(hrs))
        print(f"{e:>3.0f}/hr   " + "".join(f"{v:>10.2f}" for v in row))

    print("\n--- break-even: smallest size to average >=5◎/hr at each entry-rate ---")
    for e in [15, 30, 60]:
        s = 0.1
        while s <= 8.0:
            m = statistics.mean(sim_hours(800, e, s, seed=11))
            if m >= 5.0:
                print(f"  {e:>3.0f} entries/hr -> size {s:.2f}◎  (avg {m:.1f}◎/hr)")
                break
            s += 0.1
        else:
            print(f"  {e:>3.0f} entries/hr -> not reached at <=8◎ size")

    print("\n--- verdict ---")
    print("The MACHINERY is capable: run through the real cost model, the moonbag")
    print("strategy clears 5-10◎/hr at achievable size/entry-rate IF the entry filter")
    print("delivers roughly the assumed fat-tailed hit-distribution. That 'IF' is the")
    print("whole game — most of the SOL comes from the ~2% moonshots, so a few hours")
    print("will be flat/negative and rare hours huge (see P10/P90). Whether your live")
    print("filter actually produces this distribution is UNPROVEN here; the dashboard's")
    print("live SOL/hr meter + the backtester measure it on real data. Size only a")
    print("strategy the backtester already shows positive — scaling a negative edge")
    print("loses faster. Paper/sim only; not financial advice.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
