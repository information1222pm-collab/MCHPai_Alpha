#!/usr/bin/env python3
"""MCHPAI win/loss classifier — XGBoost, with honest accuracy tracking.

Predicts whether a token is a *winner* from only its **first 3 swaps**.

  label   : price reaches >= 2x AFTER the feature window (a real, measured forward
            move — not a future fate we haven't seen).
  features: first-3-swaps only — early flow, buyers, entropy, concentration, price
            slope, point-in-time creator history. No feature derived from after
            the prediction point ⇒ zero leakage.
  split   : time-ordered (train on older births, test on newer) ⇒ mimics live use.

Accuracy is tracked in data/ml.db across runs, so as the corpus grows you can see
whether the model actually learns. Raw accuracy is reported against the
majority-class baseline (with ~11% winners, predicting 'all lose' scores ~89%),
plus AUC / precision / recall, which is what actually matters under imbalance.

    python scripts/predict.py            # train, evaluate, log a run
    python scripts/predict.py --track    # show accuracy history across runs

HONESTY: with a small, young corpus this is a proof-of-pipeline; metrics are not
yet trustworthy and will fluctuate. It becomes meaningful only with scale + mature
labels. The harness is correct; the data is not yet sufficient.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import time
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np

ACQ_DB = os.environ.get("ACQUIRE_DB", "data/acquisition.db")
ML_DB = os.environ.get("ML_DB", "data/ml.db")
MODEL_PATH = "models/saved_models/win_classifier.json"

FEATURE_SWAPS = 3         # features may only use a token's first 3 swaps
WIN_MULTIPLE = 2.0        # "winner" = price >=2x AFTER the feature window
MIN_TOTAL_SWAPS = 5       # need a future to predict (3 for features + >=2 ahead)

FEATURES = [
    "early_n_swaps", "early_buys", "early_sells", "early_unique_buyers",
    "early_volume_sol", "early_buy_sol", "early_flow_imbalance",
    "early_buyer_entropy", "early_top_buyer_share", "early_price_slope",
    "log_first_price", "creator_prior_launches", "is_pumpfun",
]


def ro(path: str) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)


def _entropy(weights: list[float]) -> float:
    a = np.array([w for w in weights if w > 0], dtype=float)
    if a.size <= 1:
        return 0.0
    p = a / a.sum()
    return float(-np.sum(p * np.log(p)) / np.log(len(a)))


def build_dataset(acq: sqlite3.Connection):
    # point-in-time creator history: births sorted by time
    births = acq.execute(
        "SELECT mint, creator, birth_timestamp, launchpad FROM token_births").fetchall()
    birth_by_mint = {b[0]: b for b in births}
    creator_births = defaultdict(list)
    for mint, creator, bts, _lp in births:
        if creator and bts:
            creator_births[creator].append(bts)
    for c in creator_births:
        creator_births[c].sort()

    X, y, meta = [], [], []
    mints = [r[0] for r in acq.execute(
        "SELECT mint FROM swaps GROUP BY mint HAVING count(*) >= ?", (MIN_TOTAL_SWAPS,)).fetchall()]

    for mint in mints:
        swaps = acq.execute(
            "SELECT wallet, side, sol_amount, price, ts FROM swaps WHERE mint=? ORDER BY ts, slot",
            (mint,)).fetchall()
        # keep only priced swaps, preserving order
        swaps = [s for s in swaps if s[3]]
        if len(swaps) < MIN_TOTAL_SWAPS:
            continue
        b = birth_by_mint.get(mint)
        birth_ts = b[2] if b and b[2] else swaps[0][4]

        # feature window = first FEATURE_SWAPS swaps; label = pump AFTER it (leak-free)
        early = swaps[:FEATURE_SWAPS]
        future_prices = [s[3] for s in swaps[FEATURE_SWAPS:]]
        anchor_price = early[-1][3]
        first_price = early[0][3]
        if anchor_price <= 0 or first_price <= 0 or not future_prices:
            continue
        label = 1 if (max(future_prices) / anchor_price) >= WIN_MULTIPLE else 0
        e_buys = [s for s in early if s[1] == "buy"]
        e_sells = [s for s in early if s[1] == "sell"]
        e_buy_sol = sum(s[2] for s in e_buys)
        e_sell_sol = sum(s[2] for s in e_sells)
        e_vol = e_buy_sol + e_sell_sol
        e_prices = [s[3] for s in early if s[3]]
        slope = 0.0
        if len(e_prices) >= 2:
            xs = np.arange(len(e_prices), dtype=float)
            slope = float(np.polyfit(xs, np.array(e_prices, dtype=float), 1)[0])
        buyer_sol = defaultdict(float)
        for s in e_buys:
            buyer_sol[s[0]] += s[2]
        top_share = (max(buyer_sol.values()) / e_buy_sol) if e_buy_sol > 0 else 0.0

        creator = b[1] if b else None
        prior = 0
        if creator and creator in creator_births:
            prior = sum(1 for t in creator_births[creator] if t < birth_ts)

        feat = {
            "early_n_swaps": len(early),
            "early_buys": len(e_buys), "early_sells": len(e_sells),
            "early_unique_buyers": len({s[0] for s in e_buys}),
            "early_volume_sol": e_vol, "early_buy_sol": e_buy_sol,
            "early_flow_imbalance": (e_buy_sol - e_sell_sol) / e_vol if e_vol else 0.0,
            "early_buyer_entropy": _entropy(list(buyer_sol.values())),
            "early_top_buyer_share": top_share,
            "early_price_slope": slope,
            "log_first_price": float(np.log10(first_price)) if first_price > 0 else 0.0,
            "creator_prior_launches": prior,
            "is_pumpfun": 1.0 if (b and b[3] == "pumpfun") else 0.0,
        }
        X.append([feat[k] for k in FEATURES])
        y.append(label)
        meta.append({"mint": mint, "birth_ts": birth_ts})

    return np.array(X, dtype=float), np.array(y, dtype=int), meta


def ml_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(ML_DB) or ".", exist_ok=True)
    c = sqlite3.connect(ML_DB, timeout=10)
    c.executescript("""
      CREATE TABLE IF NOT EXISTS runs(
        ts INTEGER, n_samples INTEGER, n_pos INTEGER, n_train INTEGER, n_test INTEGER,
        baseline_acc REAL, accuracy REAL, auc REAL, precision REAL, recall REAL,
        f1 REAL, cv_auc_mean REAL, cv_auc_std REAL, beats_baseline INTEGER);
      CREATE TABLE IF NOT EXISTS predictions(
        run_ts INTEGER, mint TEXT, prob REAL, pred INTEGER, actual INTEGER);
    """)
    return c


def train_and_eval() -> dict:
    from sklearn.metrics import (accuracy_score, f1_score, precision_score,
                                 recall_score, roc_auc_score)
    from sklearn.model_selection import StratifiedKFold
    import xgboost as xgb

    acq = ro(ACQ_DB)
    X, y, meta = build_dataset(acq)
    acq.close()
    n, n_pos = len(y), int(y.sum())
    res: dict = {"n_samples": n, "n_pos": n_pos}
    if n < 30 or n_pos < 5 or n_pos == n:
        res["error"] = (f"insufficient data for a trustworthy model "
                        f"(n={n}, winners={n_pos}). Harness ready; collect more.")
        return res

    # time-ordered split: train on older births, test on newer (no leakage)
    order = np.argsort([m["birth_ts"] for m in meta])
    X, y, meta = X[order], y[order], [meta[i] for i in order]
    cut = int(n * 0.7)
    Xtr, Xte, ytr, yte = X[:cut], X[cut:], y[:cut], y[cut:]

    spw = max(1.0, (len(ytr) - ytr.sum()) / max(ytr.sum(), 1))
    clf = xgb.XGBClassifier(
        n_estimators=120, max_depth=3, learning_rate=0.08,
        subsample=0.8, colsample_bytree=0.8, scale_pos_weight=spw,
        eval_metric="auc", reg_lambda=1.0)
    clf.fit(Xtr, ytr)

    prob = clf.predict_proba(Xte)[:, 1]
    pred = (prob >= 0.5).astype(int)
    baseline = max(np.mean(yte == 0), np.mean(yte == 1)) if len(yte) else 0.0
    acc = accuracy_score(yte, pred) if len(yte) else 0.0
    try:
        auc = roc_auc_score(yte, prob) if len(set(yte)) > 1 else float("nan")
    except Exception:
        auc = float("nan")

    # stratified CV AUC over the whole set for a more stable read
    cv_aucs = []
    if n_pos >= 5:
        skf = StratifiedKFold(n_splits=min(5, n_pos), shuffle=True, random_state=42)
        for tri, tei in skf.split(X, y):
            if len(set(y[tri])) < 2 or len(set(y[tei])) < 2:
                continue
            m = xgb.XGBClassifier(n_estimators=120, max_depth=3, learning_rate=0.08,
                                  subsample=0.8, colsample_bytree=0.8,
                                  scale_pos_weight=spw, eval_metric="auc")
            m.fit(X[tri], y[tri])
            try:
                cv_aucs.append(roc_auc_score(y[tei], m.predict_proba(X[tei])[:, 1]))
            except Exception:
                pass

    importances = sorted(zip(FEATURES, clf.feature_importances_),
                         key=lambda kv: -kv[1])
    res.update({
        "n_train": int(cut), "n_test": int(n - cut),
        "baseline_acc": round(float(baseline), 3),
        "accuracy": round(float(acc), 3),
        "auc": round(float(auc), 3) if auc == auc else None,
        "precision": round(float(precision_score(yte, pred, zero_division=0)), 3),
        "recall": round(float(recall_score(yte, pred, zero_division=0)), 3),
        "f1": round(float(f1_score(yte, pred, zero_division=0)), 3),
        "cv_auc_mean": round(float(np.mean(cv_aucs)), 3) if cv_aucs else None,
        "cv_auc_std": round(float(np.std(cv_aucs)), 3) if cv_aucs else None,
        "beats_baseline": bool(acc > baseline),
        "top_features": [(f, round(float(i), 3)) for f, i in importances[:6]],
    })

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    clf.save_model(MODEL_PATH)

    db = ml_db()
    ts = int(time.time())
    db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
               (ts, n, n_pos, int(cut), int(n - cut), res["baseline_acc"], res["accuracy"],
                res.get("auc"), res["precision"], res["recall"], res["f1"],
                res.get("cv_auc_mean"), res.get("cv_auc_std"), int(res["beats_baseline"])))
    for p, pr, a, mt in zip(prob, pred, yte, meta[cut:]):
        db.execute("INSERT INTO predictions VALUES (?,?,?,?,?)",
                   (ts, mt["mint"], float(p), int(pr), int(a)))
    db.commit()
    db.close()
    return res


def show_history() -> None:
    db = ml_db()
    rows = db.execute(
        "SELECT ts,n_samples,n_pos,baseline_acc,accuracy,auc,cv_auc_mean,beats_baseline "
        "FROM runs ORDER BY ts").fetchall()
    if not rows:
        print("no runs yet")
        return
    print(f"{'time':<20}{'N':>6}{'win':>5}{'base':>7}{'acc':>7}{'auc':>7}{'cvAUC':>7}{'beats?':>8}")
    for ts, n, npos, base, acc, auc, cv, beats in rows:
        t = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        print(f"{t:<20}{n:>6}{npos:>5}{base:>7}{acc:>7}"
              f"{(auc if auc is not None else float('nan')):>7.3f}"
              f"{(cv if cv is not None else float('nan')):>7.3f}{('YES' if beats else 'no'):>8}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", action="store_true", help="show accuracy history")
    args = ap.parse_args()
    if args.track:
        show_history()
        return 0
    res = train_and_eval()
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
