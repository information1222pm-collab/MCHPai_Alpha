# models/

Trainable models and the training harness. Each subdirectory is a model family
with the same shape: a `train.py` that pulls a dataset from ClickHouse/MinIO,
trains, evaluates, and publishes an artifact + manifest to the MinIO `models`
bucket. The `prediction-engine` loads whatever is published via its
`ModelRegistry` — the serving interface never changes as models evolve.

```
models/
├── base.py                 # Trainer/Model interfaces + dataset + registry publish
├── xgboost/                # gradient boosted trees (default buy_probability)
├── lightgbm/
├── catboost/
├── gnn/                    # graph neural nets over the wallet graph (Neo4j → PyG)
├── transformers/          # sequence models over wallet/token event streams
├── reinforcement_learning/# execution & sizing policies
└── saved_models/          # local artifact cache (gitignored)
```

## Targets

| Target            | Type            | Default family |
|-------------------|-----------------|----------------|
| `buy_probability` | binary classif. | XGBoost        |
| `risk_score`      | regression      | LightGBM       |
| `expected_value`  | derived         | analytic       |
| wallet embeddings | representation  | GNN            |
| sizing policy     | control         | RL (PPO)       |

## Promotion flow

`train → evaluate (walk-forward, no leakage) → register (MinIO) → shadow →
canary → promote`. Promotion only happens if the candidate beats the incumbent
on out-of-sample EV after costs.
