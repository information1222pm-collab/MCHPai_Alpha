#!/usr/bin/env python3
"""Pattern-discovery engine — learn WHICH early signals predict winners.

Mines the collected real swaps: for every token, snapshots its early features at a
decision point, labels whether it subsequently RAN (forward max >= target x), then
(1) ranks each feature by predictive lift and (2) fits a regularized logistic model
(train/test split, AUC) to find the combined pattern. Outputs the discovered
patterns and synthesizes an entry rule from them.

This is the "signals and patterns discovered over time" core: re-run it as more
data accumulates and the patterns sharpen. Honest about predictive power — if the
features don't separate winners, it says so.

    ACQUIRE_DB=data/public_live.db python3 scripts/discover.py
    ACQUIRE_DB=data/public_live.db python3 scripts/discover.py --runx 2.0 --decide 25
"""
from __future__ import annotations

import argparse
import os
import statistics
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scripts.research as R

FEATURES = ["buyers", "ratio", "netflow", "smart", "accel", "liq", "whale", "mom", "organic", "age"]


def build_dataset(decide_age: float, runx: float):
    """One row per token: early features at the decision point + win label."""
    rows, wfirst, ticks = R.load()
    by_mint: dict[str, list] = {}
    for r in rows:
        by_mint.setdefault(r[0], []).append(r)
    X, y, mints = [], [], []
    for mint, srows in by_mint.items():
        st = R.TState(srows[0][5])
        birth = srows[0][5]
        decided = None
        prev_buyers, prev_ts = 0, birth
        whale, nbuys = 0.0, 0
        for (_m, wallet, side, sol, price, ts) in srows:
            st.update(side, sol, price, wallet, wfirst)
            if side == "buy":
                nbuys += 1
                if sol >= whale:
                    whale = sol
            age = ts - birth
            if decided is None and age >= decide_age and st.buyers and st.last > 0:
                f = st.feat(ts)
                accel = (len(st.buyers) - prev_buyers) / max(ts - prev_ts, 1)
                decided = dict(price=st.last, ts=ts,
                               feat=[len(st.buyers), f.ratio(), (f.buy_vol - f.sell_vol) / (f.buy_vol + f.sell_vol + 1e-9),
                                     len(st.smart), accel, st.liq(), 1.0 if whale >= 3 else 0.0,
                                     f.momentum(5), min(1.0, len(st.buyers) / max(nbuys, 1)), age])
            prev_buyers, prev_ts = len(st.buyers), ts
        if decided is None:
            continue
        # forward outcome: sanitized max price AFTER the decision point
        fwd_max = decided["price"]
        st2 = R.TState(srows[0][5])
        for (_m, wallet, side, sol, price, ts) in srows:
            st2.update(side, sol, price, wallet, wfirst)
            if ts > decided["ts"] and st2.last > 0:
                fwd_max = max(fwd_max, st2.last)
        win = 1 if fwd_max / decided["price"] >= runx else 0
        X.append(decided["feat"]); y.append(win); mints.append(mint)
    return np.array(X, float), np.array(y, int), mints


def lift_table(X, y):
    print(f"\n{'feature':>9}{'win|hi':>9}{'win|lo':>9}{'lift':>7}  (P(run) when feature high vs low)")
    base = y.mean()
    out = []
    for i, name in enumerate(FEATURES):
        col = X[:, i]
        med = np.median(col)
        hi = y[col > med]; lo = y[col <= med]
        ph = hi.mean() if len(hi) else 0.0
        pl = lo.mean() if len(lo) else 0.0
        lift = ph / (pl + 1e-9)
        out.append((name, ph, pl, lift))
    for name, ph, pl, lift in sorted(out, key=lambda r: -abs(r[3] - 1)):
        flag = " ★" if abs(lift - 1) > 0.4 and (ph > base or pl > base) else ""
        print(f"{name:>9}{ph:>9.2f}{pl:>9.2f}{lift:>7.2f}{flag}")
    print(f"base P(run >= target): {base:.2f}")
    return out


def logreg(X, y, iters=4000, lr=0.1, l2=1e-2, seed=0):
    rng = np.random.default_rng(seed)
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Xs = (X - mu) / sd
    n = len(y)
    idx = rng.permutation(n)
    cut = int(n * 0.7)
    tr, te = idx[:cut], idx[cut:]
    w = np.zeros(Xs.shape[1]); b = 0.0
    for _ in range(iters):
        z = Xs[tr] @ w + b
        p = 1 / (1 + np.exp(-z))
        g = p - y[tr]
        w -= lr * (Xs[tr].T @ g / len(tr) + l2 * w)
        b -= lr * g.mean()
    def auc(ix):
        if len(ix) == 0:
            return 0.5
        s = Xs[ix] @ w + b
        pos = s[y[ix] == 1]; neg = s[y[ix] == 0]
        if len(pos) == 0 or len(neg) == 0:
            return 0.5
        return float(np.mean([1.0 if a > b_ else 0.5 if a == b_ else 0.0 for a in pos for b_ in neg]))
    return w, b, mu, sd, auc(tr), auc(te)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runx", type=float, default=1.5, help="forward multiple that defines a 'winner'")
    ap.add_argument("--decide", type=float, default=20, help="decision age (s) to snapshot features")
    args = ap.parse_args()

    X, y, mints = build_dataset(args.decide, args.runx)
    if len(y) < 30:
        print(f"only {len(y)} usable tokens — need more data (run collect_public.py longer)")
        return 1
    print(f"=== PATTERN DISCOVERY · {len(y)} tokens · decision@{args.decide:.0f}s · "
          f"winner = forward >= {args.runx:.1f}x · winners {int(y.sum())} ({y.mean()*100:.0f}%) ===")
    lift_table(X, y)
    w, b, mu, sd, auc_tr, auc_te = logreg(X, y)
    print(f"\nlogistic model AUC  train {auc_tr:.2f} · test {auc_te:.2f}   "
          f"({'has predictive signal' if auc_te > 0.58 else 'weak/none on this data'})")
    order = np.argsort(-np.abs(w))
    print("discovered pattern weights (standardized; + = predicts a run):")
    for i in order:
        print(f"  {FEATURES[i]:>9}: {w[i]:+.2f}")
    # synthesize a rule from the strongest drivers — direction follows the sign of the weight
    strong = [i for i in order if abs(w[i]) > 0.15][:5]
    print("\n--- synthesized entry pattern (strongest drivers, correct direction) ---")
    if strong and auc_te > 0.55:
        win_rows = X[y == 1]
        rule = []
        for i in strong:
            thr = float(np.median(win_rows[:, i]))
            op = ">=" if w[i] > 0 else "<="     # negative weight (e.g. age) => prefer LOW
            rule.append(f"{FEATURES[i]} {op} {thr:.2f}")
        print("  ENTER when: " + "  AND  ".join(rule))
        print("  (feed these into a dashboard strategy; re-discover as data grows to sharpen)")
    else:
        print("  No reliable pattern yet — features don't separate winners on this sample.")
        print("  Gather more data and re-run; the discovery sharpens with volume.")
    print("\nHonest: discovered on one real window — predictive on held-out tokens only if test")
    print("AUC > ~0.6. Re-run continuously as data accumulates; that's the 'over time' learning.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
