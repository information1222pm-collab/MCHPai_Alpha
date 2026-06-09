#!/usr/bin/env bash
# MCHPAI — continuous learning loop (single host).
#
# Brings the system into a genuine *learning and improving* state:
#   1) acquisition runs forever (the corpus keeps growing)
#   2) analysis + models retrain on an interval (they learn from new data)
#   3) the Observation Center serves the live, auto-refreshing dashboard
#
# The dashboard's tracking tables (model accuracy, RL reward) then show the trend
# over time — i.e. whether the system is actually improving, not just running.
#
# Requires: HELIUS_API_KEY in the environment. Open http://localhost:8888
#
#   HELIUS_API_KEY=xxxx bash scripts/run_all.sh
set -euo pipefail
cd "$(dirname "$0")/.."

: "${HELIUS_API_KEY:?set HELIUS_API_KEY first}"
RETRAIN_EVERY="${RETRAIN_EVERY:-600}"   # seconds between retrains
export HELIUS_API_KEY

echo "[run_all] starting continuous learning loop"
echo "[run_all] dashboard → http://localhost:${OBSERVATORY_PORT:-8888}"

# 1) continuous acquisition (restarts each window so it never stops)
( while true; do
    python3 scripts/acquire.py --minutes 30 || true
  done ) &
ACQ=$!

# 2) periodic analysis + retraining (the 'learning' part)
( while true; do
    sleep "${RETRAIN_EVERY}"
    echo "[run_all] retraining on the growing corpus…"
    python3 scripts/analyze.py   >/dev/null 2>&1 || true   # per-token + pattern mining
    python3 scripts/predict.py   >/dev/null 2>&1 || true   # XGBoost win/loss (logs a run)
    python3 scripts/rl_agent.py  >/dev/null 2>&1 || true   # RL agent     (logs a run)
    python3 scripts/snapshot.py  >/dev/null 2>&1 || true   # refresh the shareable snapshot
    echo "[run_all] retrain cycle done"
  done ) &
TRAIN=$!

# 3) the live observation center (foreground)
trap 'kill $ACQ $TRAIN 2>/dev/null || true' EXIT INT TERM
python3 scripts/observatory.py
