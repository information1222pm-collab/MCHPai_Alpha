# Machine Learning

## The five scores

| Score                 | Range  | Produced by                              |
|-----------------------|--------|------------------------------------------|
| `wallet_alpha_score`  | 0–100  | `prediction_engine.scoring` (composite)  |
| `cluster_score`       | 0–100  | `prediction_engine.scoring`              |
| `buy_probability`     | 0–1    | model (XGBoost) / transparent baseline   |
| `expected_value`      | bps    | analytic from `buy_probability` + costs  |
| `risk_score`          | 0–100  | structural (`tokens.safety`) + model     |

## Baselines first, models second

Every score has a **transparent baseline** (`scoring.py`) so the platform is
fully functional before any model is trained — and so we always have a sanity
check and a fallback. Models *override* baselines via the `ModelRegistry`; if no
model is published, baselines serve.

## `wallet_alpha_score`

Weighted, winsorized composite of the six axes with **empirical-Bayes shrinkage**:
win rate is pulled toward the population prior by sample size, and a confidence
multiplier scales the whole score, so a 2-for-2 wallet can't outrank a proven one.

## `buy_probability`

Default model: **XGBoost** (`models/xgboost`). Ensemble members: LightGBM,
CatBoost. Features come from the online store (Redis) at serve time, the offline
store (ClickHouse) at train time — same definitions, no skew. Labels are forward
realized outcomes; training is **walk-forward** (no look-ahead).

## `expected_value`

`EV_bps = p·up − (1−p)·down − fees − slippage` (`forecasting.expected_value`).
This is what the strategy-engine actually optimizes — probability alone isn't
tradable; EV after costs is.

## Model lifecycle

`train → walk-forward eval → register (MinIO + manifest) → shadow → canary →
promote`. A candidate is promoted only if it beats the incumbent on
out-of-sample EV after costs. The serving interface (`predict(features)->float`)
is identical across XGBoost, LightGBM, CatBoost, GNNs, and transformers — so the
model zoo can grow without touching `prediction-engine`.

## Where it's going

* **GNNs** (`models/gnn`) — learn wallet/cluster embeddings from the Neo4j graph
  (export → PyTorch Geometric) and feed them as features.
* **Transformers** (`models/transformers`) — sequence models over per-wallet/token
  event streams to capture temporal structure.
* **RL** (`models/reinforcement_learning`) — learn the execution/sizing policy
  (tip, slippage, size) against a simulated fill model; off the live path until
  proven in shadow.
