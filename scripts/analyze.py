#!/usr/bin/env python3
"""MCHPAI analysis engine.

Generates a complete analysis report per token from the acquired reality, then —
once >=100 reports exist — mines the corpus for cross-token patterns and
consistencies. Designed to run continuously (``--watch``).

It reads the acquisition store READ-ONLY (never locks the live acquirer) and
writes reports + patterns to a separate analysis DB and JSON files. It reuses the
existing instrument (entropy, ground-truth, schemas) — no new intelligence, just
analysis of what reality has said so far.

    python scripts/analyze.py                 # one pass: reports + (meta if >=100)
    python scripts/analyze.py --watch 60      # re-analyze every 60s
    python scripts/analyze.py --report <MINT> # print one token's report

HONESTY: with a small / young corpus most token outcomes are still 'pending'
(a token needs hours to reveal a 2x or a rug). Findings here are
hypothesis-generating, not trade signals, until outcomes mature.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

import numpy as np

from mchpai_common.entropy import buyer_entropy
from mchpai_common.ground_truth import SnapshotPoint, compute_ground_truth

ACQ_DB = os.environ.get("ACQUIRE_DB", "data/acquisition.db")
ANALYSIS_DB = os.environ.get("ANALYSIS_DB", "data/analysis.db")
REPORTS_DIR = "data/reports"
PATTERNS_PATH = "data/analysis/patterns.json"


def ro(path: str) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)


def analysis_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(ANALYSIS_DB) or ".", exist_ok=True)
    c = sqlite3.connect(ANALYSIS_DB, timeout=10)
    c.execute("CREATE TABLE IF NOT EXISTS reports(mint TEXT PRIMARY KEY, generated_at INTEGER, report TEXT)")
    return c


# ----------------------------------------------------------------- per token
def token_report(acq: sqlite3.Connection, mint: str) -> dict:
    birth = acq.execute(
        "SELECT birth_slot, birth_timestamp, creator, launchpad FROM token_births WHERE mint=?",
        (mint,)).fetchone()
    swaps = acq.execute(
        "SELECT wallet, side, sol_amount, token_amount, price, slot, ts FROM swaps "
        "WHERE mint=? ORDER BY ts, slot", (mint,)).fetchall()

    creator = birth[2] if birth else None
    launchpad = birth[3] if birth else None
    birth_ts = birth[1] if birth and birth[1] else (swaps[0][6] if swaps else None)

    rep: dict = {
        "mint": mint, "creator": creator, "launchpad": launchpad,
        "birth_slot": birth[0] if birth else None, "birth_ts": birth_ts,
        "has_birth": bool(birth), "n_swaps": len(swaps),
    }
    if not swaps:
        rep.update({"status": "no_trades"})
        return rep

    buys = [s for s in swaps if s[1] == "buy"]
    sells = [s for s in swaps if s[1] == "sell"]
    buy_sol = sum(s[2] for s in buys)
    sell_sol = sum(s[2] for s in sells)
    vol = buy_sol + sell_sol
    prices = [s[4] for s in swaps if s[4]]
    first_p = prices[0] if prices else None
    last_p = prices[-1] if prices else None
    max_p = max(prices) if prices else None

    buyer_sol = defaultdict(float)
    for w, side, sol, *_ in buys:
        buyer_sol[w] += sol
    top_buyer_share = (max(buyer_sol.values()) / buy_sol) if buy_sol > 0 else 0.0

    age = (swaps[-1][6] - birth_ts) if birth_ts else (swaps[-1][6] - swaps[0][6])

    # preliminary outcome via the real ground-truth engine (from price/age series)
    pts = [SnapshotPoint(age_seconds=max(0.0, s[6] - (birth_ts or swaps[0][6])),
                         price_sol=s[4]) for s in swaps if s[4]]
    gt = compute_ground_truth(mint, datetime.fromtimestamp(birth_ts or swaps[0][6], tz=timezone.utc), pts)

    rep.update({
        "status": "analyzed",
        "age_seconds": age,
        "n_buys": len(buys), "n_sells": len(sells),
        "unique_buyers": len({s[0] for s in buys}),
        "unique_sellers": len({s[0] for s in sells}),
        "unique_wallets": len({s[0] for s in swaps}),
        "volume_sol": round(vol, 6),
        "buy_sol": round(buy_sol, 6), "sell_sol": round(sell_sol, 6),
        "flow_imbalance": round((buy_sol - sell_sol) / vol, 4) if vol else 0.0,
        "first_price": first_p, "last_price": last_p, "max_price": max_p,
        "max_multiple": round(gt.max_multiple, 3),
        "current_multiple": round((last_p / first_p), 3) if first_p and last_p else None,
        "buyer_entropy": round(buyer_entropy(dict(buyer_sol)), 4) if buyer_sol else 0.0,
        "top_buyer_share": round(top_buyer_share, 4),
        "outcome": gt.outcome.value,
        "achieved_2x": gt.label(2, "1h"), "achieved_5x": gt.label(5, "1h"),
        "achieved_10x": gt.label(10, "1h"),
        "is_final": gt.is_final,
        "generated_at": int(time.time()),
    })
    return rep


def all_mints(acq: sqlite3.Connection) -> list[str]:
    rows = acq.execute(
        "SELECT mint FROM token_births UNION SELECT mint FROM swaps").fetchall()
    return [r[0] for r in rows]


def generate_reports(acq, store) -> int:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    n = 0
    for mint in all_mints(acq):
        rep = token_report(acq, mint)
        store.execute("INSERT OR REPLACE INTO reports VALUES (?,?,?)",
                      (mint, rep.get("generated_at", int(time.time())), json.dumps(rep)))
        with open(f"{REPORTS_DIR}/{mint}.json", "w") as f:
            json.dump(rep, f, indent=2)
        n += 1
    store.commit()
    return n


# ----------------------------------------------------------------- meta analysis
def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    if x.size < 5 or x.std() < 1e-12 or y.std() < 1e-12:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def meta_analysis(store, acq) -> dict:
    reports = [json.loads(r[0]) for r in store.execute(
        "SELECT report FROM reports").fetchall()]
    analyzed = [r for r in reports if r.get("status") == "analyzed"]
    out: dict = {"generated_at": datetime.now(timezone.utc).isoformat(),
                 "n_reports": len(reports), "n_analyzed": len(analyzed)}
    if len(reports) < 100:
        out["note"] = f"meta-analysis activates at 100 reports ({len(reports)} so far)"
        return out

    # ---- feature matrix vs. max_multiple (hypothesis generation) ----
    feats = ["unique_buyers", "n_swaps", "volume_sol", "flow_imbalance",
             "buyer_entropy", "top_buyer_share", "n_sells"]
    target = np.array([r["max_multiple"] for r in analyzed], dtype=float)
    correlations = {}
    for f in feats:
        x = np.array([r.get(f, 0.0) for r in analyzed], dtype=float)
        correlations[f] = round(_pearson(x, target), 3)
    out["correlations_with_max_multiple"] = dict(
        sorted(correlations.items(), key=lambda kv: -abs(kv[1])))

    # ---- distributions / consistencies ----
    mults = sorted(r["max_multiple"] for r in analyzed)
    out["consistencies"] = {
        "median_max_multiple": round(float(np.median(mults)), 3),
        "p90_max_multiple": round(float(np.percentile(mults, 90)), 3),
        "share_reached_2x": round(np.mean([m >= 2 for m in mults]), 3),
        "share_reached_5x": round(np.mean([m >= 5 for m in mults]), 3),
        "median_unique_buyers": int(np.median([r["unique_buyers"] for r in analyzed])),
        "median_volume_sol": round(float(np.median([r["volume_sol"] for r in analyzed])), 3),
        "outcome_breakdown": dict(Counter(r["outcome"] for r in analyzed)),
        "share_outcomes_final": round(np.mean([r["is_final"] for r in analyzed]), 3),
    }

    # ---- repeat creators ----
    by_creator = defaultdict(list)
    for r in analyzed:
        if r.get("creator"):
            by_creator[r["creator"]].append(r["max_multiple"])
    serial = {c: {"launches": len(v), "median_multiple": round(float(np.median(v)), 3)}
              for c, v in by_creator.items() if len(v) >= 2}
    out["repeat_creators"] = dict(sorted(serial.items(),
                                  key=lambda kv: -kv[1]["launches"])[:15])

    # ---- cross-token wallets (candidate snipers / smart money) ----
    wallet_mints = defaultdict(set)
    for mint_row in acq.execute("SELECT DISTINCT wallet, mint FROM swaps").fetchall():
        wallet_mints[mint_row[0]].add(mint_row[1])
    serial_wallets = sorted(((w, len(ms)) for w, ms in wallet_mints.items()),
                            key=lambda kv: -kv[1])[:20]
    out["cross_token_wallets"] = [{"wallet": w, "tokens_traded": n}
                                  for w, n in serial_wallets if n >= 2]

    # ---- preliminary actionable hypotheses (NOT trade signals) ----
    strong = [(f, c) for f, c in out["correlations_with_max_multiple"].items()
              if abs(c) >= 0.2]
    out["hypotheses"] = [
        f"'{f}' shows {'positive' if c > 0 else 'negative'} correlation (r={c}) "
        f"with peak multiple — candidate signal to validate as outcomes mature."
        for f, c in strong
    ] or ["No correlation |r|>=0.2 yet; corpus too small/young for signal."]

    out["caveat"] = ("Outcomes are largely immature (tokens are minutes old); "
                     "treat all patterns as hypotheses pending mature ground truth.")
    return out


# ----------------------------------------------------------------- driver
def run_once(verbose: bool = True) -> dict:
    acq = ro(ACQ_DB)
    store = analysis_db()
    n = generate_reports(acq, store)
    patterns = meta_analysis(store, acq)
    os.makedirs(os.path.dirname(PATTERNS_PATH) or ".", exist_ok=True)
    with open(PATTERNS_PATH, "w") as f:
        json.dump(patterns, f, indent=2)
    acq.close()
    store.close()
    if verbose:
        print(f"reports generated: {n}")
        print(json.dumps(patterns, indent=2))
    return patterns


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", type=int, default=0, help="re-analyze every N seconds")
    ap.add_argument("--report", type=str, help="print a single token's report")
    args = ap.parse_args()

    if args.report:
        print(json.dumps(token_report(ro(ACQ_DB), args.report), indent=2))
        return 0
    if args.watch:
        print(f"continuous analysis every {args.watch}s (Ctrl-C to stop)")
        while True:
            try:
                p = run_once(verbose=False)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] reports={p['n_reports']} "
                      f"analyzed={p.get('n_analyzed')} status="
                      f"{'META' if p['n_reports'] >= 100 else 'collecting'}")
            except Exception as e:  # noqa: BLE001
                print(f"analysis error: {e}")
            time.sleep(args.watch)
    run_once()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
