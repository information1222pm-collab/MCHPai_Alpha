# Data Pipeline (Phase 1) — The Market Observatory

> Build the roads before the cars. Phase 1 is about acquiring the **highest
> quality ground-truth + time-series dataset possible** — because every future
> model (GNN, Temporal Fusion Transformer, RL, multi-agent) will depend more on
> data quality than on model complexity.

## The pipeline

```
 Yellowstone gRPC (failover pool, slot tracking, backpressure)
        │  raw.swaps (Redis)
        ▼
 wallet-ingestion ──► WalletBoughtToken / WalletSoldToken (NATS)
        │
        ▼
 snapshot-engine ──► multi-resolution snapshots (5s/15s/30s/60s) ──► ClickHouse `snapshots`
        │            (ordered seq + age + lifecycle phase)
        ▼
 ground-truth ──► forward labels (achieved Nx @ 1h/6h/24h/7d, rugged/survived/viral) ──► Postgres `ground_truth`
        │
        ├─► creator-intelligence ──► creator_score ──► Postgres `creator_profiles`
        │
        ▼
 feature store (online: Redis · offline: MinIO, point-in-time) ──► models (XGBoost: buy/rug/survival/10x)
```

## 1. Yellowstone ingestion — the heart

`services/execution-engine/src/ingest/` — production concerns wired:

* **Failover pool** (`endpoints.rs`): round-robin over multiple Geyser providers;
  an erroring endpoint is marked unhealthy with exponential backoff and skipped.
* **Slot tracking** (`slot.rs`): monotonic slot progress + gap detection, so the
  system knows when its view of the chain is incomplete.
* **Backpressure** (`ingest/mod.rs`): a bounded `mpsc` channel decouples the
  network stream from Redis; if Redis slows, ingestion slows instead of OOMing.

## 2. Universal swap parser — arguably more important than models

`libraries/.../parsing/` supports **Pump.fun, Pump.swap, Raydium (AMM/CLMM/CPMM),
LaunchLab, Bonk, Meteora (DLMM/Dynamic/DBC), Orca Whirlpool, Jupiter, Moonshot**.

It extracts economic truth from **balance deltas** (pre/post SOL + token balances)
rather than brittle per-DEX instruction decoding, and labels the venue by program
id (preferring the concrete pool over a router like Jupiter). Output is a single
normalized `SwapEvent { token_address, wallet_address, slot, timestamp,
sol_amount, token_amount, price, market_cap, dex, signature }`.

## 3. Snapshot engine — the gold

Every token becomes an **ordered sequence** of snapshots at four resolutions.
Each snapshot carries a monotonic `seq` and `age_seconds` and four metric groups:

* **market** — OHLC price, volume, liquidity, market cap
* **participation** — buyers, sellers, unique traders, holders, txns
* **intelligence** — buyer entropy, R0, smart-money ratio, cluster ratio, net flow
* **safety** — top-holder %, holder Gini, LP health

Each step is labeled with a **lifecycle phase** (birth → growth → viral →
distribution → death). This is the substrate sequence models will learn from.

## 4. Ground truth — the foundation of all ML

`libraries/.../ground_truth/` computes, per token, the full
`achieved[{2,5,10,25,100}x][{1h,6h,24h,7d}]` matrix, `max_multiple`,
`time_to_max`, terminal `outcome` (rugged/survived/viral), `survival_seconds`,
and `holder_retention`. Labels are only `is_final` once the 7d window closes —
**no look-ahead leakage, ever**.

## 5. Creator intelligence

`creator_score` (0..100) from a creator's launch history: launch count, rug rate,
best/median multiple, median survival, holder retention, volume, repeat-buyer
rate — Bayesian-shrunk for thin histories. A top prior for rug/survival models.

## 6. Wallet profiler (expanded)

`libraries/.../wallets/advanced.py` adds performance (ROI, Sharpe, Kelly,
expectancy), timing (entry/exit percentile, hold), conviction (avg size, scaling,
diamond-hands), and intelligence (rug avoidance, smart entry, mean reversion) →
canonical `wallet_alpha_score`.

## 7. Feature store

`libraries/.../feature_store/` — schemaless (scales to 5,000+ features),
online (Redis) / offline (MinIO) split, **point-in-time correct**, and
**sequence-native** (`get_sequence` returns ordered trajectories).

## 8. Training

`models/` — XGBoost on four targets: `buy_probability`, `rug_probability`,
`survival_probability`, `tenx_probability`. `models/dataset.py` joins
point-in-time features with frozen labels; `models/targets.py` defines the labels.

## Why sequences, not snapshots

We deliberately store **ordered, phase-annotated trajectories** rather than flat
rows. When we later add Temporal Fusion Transformers / GNNs / RL, the dataset is
already in the shape they need — `birth → growth → viral → distribution → death`
captured as sequences. We don't touch transformers until we've collected
~50k–100k newborn tokens and millions of snapshots; until then, the objective is
data quality, and the architecture is a **market observatory**.
