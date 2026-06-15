#!/usr/bin/env python3
"""MCHPAI RL agent — self-improving / self-correcting token-selection policy.

A contextual bandit (LinUCB) that, for each token, chooses SKIP / BUY / BUY_BIG
from a rich context built from all data feeds, then learns online from the
*realized* reward (simulated PnL with take-profit / stop-loss / fees). It
self-improves (online updates) and self-corrects (forgetting factor + adaptive
exploration). It is evaluated against always-buy / always-skip / oracle, run over
multiple seeds to reduce luck, and **gated to PAPER** until it provably beats
baselines on enough matured episodes — it never auto-escalates to live.

    python scripts/rl_agent.py            # train across seeds, evaluate, log a run
    python scripts/rl_agent.py --track    # accuracy/reward history across runs

HONESTY: with a small / young corpus and immature outcomes this will NOT show a
real edge; the harness reports that truthfully. It becomes meaningful only with
scale + matured win/loss labels. The policy is correct; the data is not yet
sufficient — and the agent stays in PAPER.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.reinforcement_learning import LinUCBAgent  # noqa: E402

ACQ_DB = os.environ.get("ACQUIRE_DB", "data/acquisition.db")
RL_DB = os.environ.get("RL_DB", "data/rl.db")

FEATURE_SWAPS = 3          # decision point: after the first 3 swaps (leak-free)
MIN_TOTAL_SWAPS = 5
TAKE_PROFIT = 1.0          # +100%
STOP_LOSS = -0.5           # -50%
FEE = 0.06                 # round-trip fees + slippage + priority (memecoin-realistic)
N_SEEDS = 8
MIN_EPISODES_FOR_LIVE = 2000   # promotion gate (paper until then, by design)

FEATURES = [
    "early_buys", "early_sells", "early_unique_buyers", "early_volume_sol",
    "early_flow_imbalance", "early_buyer_entropy", "early_top_buyer_share",
    "early_price_slope", "log_first_price", "creator_prior_launches",
    "early_experienced_buyers", "is_pumpfun",
]


def ro(path):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)


def _entropy(vals):
    a = np.array([v for v in vals if v > 0], dtype=float)
    if a.size <= 1:
        return 0.0
    p = a / a.sum()
    return float(-np.sum(p * np.log(p)) / np.log(len(a)))


def realized_return(anchor, future):
    """Simulated realized return of a BUY (1x) with TP/SL/fees — winner>0, loser<0."""
    for p in future:
        r = p / anchor - 1.0
        if r >= TAKE_PROFIT:
            return TAKE_PROFIT - FEE
        if r <= STOP_LOSS:
            return STOP_LOSS - FEE
    return (future[-1] / anchor - 1.0) - FEE


def build_episodes():
    acq = ro(ACQ_DB)
    births = acq.execute(
        "SELECT mint, creator, birth_timestamp, launchpad FROM token_births").fetchall()
    binfo = {b[0]: b for b in births}
    creator_hist = defaultdict(list)
    for _m, c, t, _l in births:
        if c and t:
            creator_hist[c].append(t)
    for c in creator_hist:
        creator_hist[c].sort()
    # point-in-time wallet first-seen (for the 'experienced money present' feed)
    wallet_first = {}
    for w, t in acq.execute("SELECT wallet, min(ts) FROM swaps GROUP BY wallet").fetchall():
        wallet_first[w] = t

    mints = [r[0] for r in acq.execute(
        "SELECT mint FROM swaps GROUP BY mint HAVING count(*) >= ?", (MIN_TOTAL_SWAPS,)).fetchall()]

    raw, rewards1, meta = [], [], []
    for mint in mints:
        swaps = acq.execute(
            "SELECT wallet, side, sol_amount, price, ts FROM swaps WHERE mint=? ORDER BY ts, slot",
            (mint,)).fetchall()
        swaps = [s for s in swaps if s[3]]
        if len(swaps) < MIN_TOTAL_SWAPS:
            continue
        b = binfo.get(mint)
        birth_ts = b[2] if b and b[2] else swaps[0][4]
        early = swaps[:FEATURE_SWAPS]
        future = [s[3] for s in swaps[FEATURE_SWAPS:]]
        anchor, first_p = early[-1][3], early[0][3]
        if anchor <= 0 or first_p <= 0 or not future:
            continue

        e_buys = [s for s in early if s[1] == "buy"]
        e_sells = [s for s in early if s[1] == "sell"]
        e_buy_sol = sum(s[2] for s in e_buys)
        e_vol = sum(s[2] for s in early)
        e_prices = [s[3] for s in early if s[3]]
        slope = float(np.polyfit(np.arange(len(e_prices)), e_prices, 1)[0]) if len(e_prices) >= 2 else 0.0
        bsol = defaultdict(float)
        for s in e_buys:
            bsol[s[0]] += s[2]
        top_share = (max(bsol.values()) / e_buy_sol) if e_buy_sol > 0 else 0.0
        creator = b[1] if b else None
        prior = sum(1 for t in creator_hist.get(creator, []) if t < birth_ts) if creator else 0
        experienced = sum(1 for s in early if wallet_first.get(s[0], birth_ts) < birth_ts)

        feat = {
            "early_buys": len(e_buys), "early_sells": len(e_sells),
            "early_unique_buyers": len({s[0] for s in e_buys}),
            "early_volume_sol": e_vol,
            "early_flow_imbalance": (e_buy_sol - sum(s[2] for s in e_sells)) / e_vol if e_vol else 0.0,
            "early_buyer_entropy": _entropy(list(bsol.values())),
            "early_top_buyer_share": top_share, "early_price_slope": slope,
            "log_first_price": float(np.log10(first_p)),
            "creator_prior_launches": prior, "early_experienced_buyers": experienced,
            "is_pumpfun": 1.0 if (b and b[3] == "pumpfun") else 0.0,
        }
        raw.append([feat[k] for k in FEATURES])
        rewards1.append(realized_return(anchor, future))
        meta.append({"mint": mint, "birth_ts": birth_ts})
    acq.close()

    if not raw:
        return None
    X = np.array(raw, dtype=float)
    mu, sd = X.mean(0), X.std(0)
    sd[sd < 1e-9] = 1.0
    Xz = np.hstack([(X - mu) / sd, np.ones((len(X), 1))])  # + bias term
    order = np.argsort([m["birth_ts"] for m in meta])      # time order: past→future
    eps = []
    for i in order:
        r1 = float(rewards1[i])
        eps.append({"x": Xz[i], "reward": [0.0, r1, 2.0 * r1], "meta": meta[i]})
    return eps


def run_seed(episodes, seed):
    agent = LinUCBAgent(3, len(episodes[0]["x"]), seed=seed)
    cum = 0.0
    actions = [0, 0, 0]
    buys = buy_wins = 0
    for ep in episodes:
        a = agent.select(ep["x"])
        r = ep["reward"][a]
        agent.update(a, ep["x"], r)
        cum += r
        actions[a] += 1
        if a >= 1:
            buys += 1
            buy_wins += int(ep["reward"][1] > 0)
    return cum, actions, buys, buy_wins


def evaluate():
    episodes = build_episodes()
    if not episodes or len(episodes) < 30:
        n = len(episodes) if episodes else 0
        return {"n_episodes": n,
                "error": f"insufficient episodes for RL ({n}); harness ready, collect more."}

    n = len(episodes)
    always_buy = sum(ep["reward"][1] for ep in episodes)
    always_big = sum(ep["reward"][2] for ep in episodes)
    oracle = sum(max(ep["reward"]) for ep in episodes)        # perfect hindsight
    base_win_rate = float(np.mean([ep["reward"][1] > 0 for ep in episodes]))

    cums, acts, all_buys, all_wins = [], np.zeros(3), 0, 0
    for s in range(N_SEEDS):
        cum, a, buys, wins = run_seed(episodes, seed=s)
        cums.append(cum)
        acts += np.array(a)
        all_buys += buys
        all_wins += wins
    agent_mean = float(np.mean(cums))
    agent_std = float(np.std(cums))
    buy_win_rate = (all_wins / all_buys) if all_buys else 0.0

    promoted = (agent_mean > 0 and agent_mean > always_buy and n >= MIN_EPISODES_FOR_LIVE)
    return {
        "n_episodes": n,
        "agent_reward_mean": round(agent_mean, 3), "agent_reward_std": round(agent_std, 3),
        "baseline_always_buy": round(always_buy, 3),
        "baseline_always_big": round(always_big, 3),
        "baseline_always_skip": 0.0,
        "oracle_upper_bound": round(oracle, 3),
        "token_win_rate": round(base_win_rate, 3),
        "agent_buy_win_rate": round(buy_win_rate, 3),
        "avg_actions_per_seed": {"skip": round(acts[0] / N_SEEDS, 1),
                                 "buy": round(acts[1] / N_SEEDS, 1),
                                 "buy_big": round(acts[2] / N_SEEDS, 1)},
        "beats_always_buy": bool(agent_mean > always_buy),
        "beats_always_skip": bool(agent_mean > 0),
        "status": "LIVE-ELIGIBLE" if promoted else "PAPER",
    }


def rl_db():
    os.makedirs(os.path.dirname(RL_DB) or ".", exist_ok=True)
    c = sqlite3.connect(RL_DB, timeout=10)
    c.execute("""CREATE TABLE IF NOT EXISTS runs(
        ts INTEGER, n INTEGER, agent REAL, agent_std REAL, always_buy REAL, oracle REAL,
        token_win_rate REAL, buy_win_rate REAL, beats_buy INTEGER, beats_skip INTEGER, status TEXT)""")
    return c


def log_run(res):
    if "error" in res:
        return
    db = rl_db()
    db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
               (int(time.time()), res["n_episodes"], res["agent_reward_mean"],
                res["agent_reward_std"], res["baseline_always_buy"], res["oracle_upper_bound"],
                res["token_win_rate"], res["agent_buy_win_rate"],
                int(res["beats_always_buy"]), int(res["beats_always_skip"]), res["status"]))
    db.commit()
    db.close()


def show_history():
    db = rl_db()
    rows = db.execute("SELECT ts,n,agent,always_buy,oracle,buy_win_rate,beats_buy,status "
                      "FROM runs ORDER BY ts").fetchall()
    if not rows:
        print("no RL runs yet")
        return
    print(f"{'time':<20}{'N':>5}{'agent':>8}{'a-buy':>8}{'oracle':>8}{'buyWin':>8}{'beats':>7}  status")
    for ts, n, ag, ab, orc, bw, beats, st in rows:
        print(f"{datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'):<20}{n:>5}"
              f"{ag:>8.2f}{ab:>8.2f}{orc:>8.2f}{bw:>8.2f}{('YES' if beats else 'no'):>7}  {st}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", action="store_true")
    args = ap.parse_args()
    if args.track:
        show_history()
        return 0
    res = evaluate()
    log_run(res)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
