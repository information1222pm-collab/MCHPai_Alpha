# System Overview

End-to-end, a token's journey through MCHPAI:

1. **Discovery** — `token-ingestion` sees a new mint on Pump.fun/Raydium/Meteora
   (or via Helius/Yellowstone) and emits `TokenCreated`.
2. **Activity** — the Rust `execution-engine` streams swaps from Yellowstone and
   publishes them to Redis `raw.swaps`; `wallet-ingestion` normalizes them into
   `WalletBoughtToken`/`WalletSoldToken` and persists trades.
3. **Profiling** — wallet trade histories produce the six behavioral axes
   (ROI, win rate, hold, conviction, risk, consistency) → `wallet_alpha_score`.
4. **Graph** — `graph-engine` records `BOUGHT`/`FUNDED`/`CO_BOUGHT` edges and
   periodically runs cluster detection → `ClusterDetected`, `cluster_score`.
5. **Features** — `feature-engine` materializes creator/liquidity/entropy/spread/
   attention features (using the domain-science libraries) → ClickHouse + Redis,
   and emits `AttentionSpike` on virality.
6. **Prediction** — `prediction-engine` computes `buy_probability`,
   `expected_value`, and `risk_score` → `PredictionGenerated`, and crosses the
   gate into `BuySignalGenerated`.
7. **Strategy** — `strategy-engine` sizes the position (fractional Kelly + caps),
   checks kill-switches, emits an `Order` to Redis `exec.orders`.
8. **Execution** — the Rust engine sizes-guards, builds the swap, attaches a Jito
   tip, submits a bundle, writes the fill, emits `TradeExecuted`.
9. **Surface** — `ranking-engine` updates leaderboards; `alert-engine` notifies;
   `api-gateway` serves the plugin UI + live WebSocket feed.

## Why these components

| Concern              | Choice            | Rationale                                  |
|----------------------|-------------------|--------------------------------------------|
| Hot path             | Rust              | predictable tail latency, no GC            |
| Analytics/models     | Python            | fastest iteration, ML ecosystem            |
| Event bus            | NATS JetStream    | lightweight, durable, replayable, simple   |
| Truth DB             | PostgreSQL        | relational integrity, transactions         |
| Time-series          | ClickHouse        | columnar scans over the firehose           |
| Graph                | Neo4j (+GDS)      | native traversal + community detection     |
| Cache / hot state    | Redis             | sub-ms shared state across Rust + Python   |
| Feature/model store  | MinIO (S3)        | versioned artifacts, cheap, portable       |

## Scaling posture

Every Python service scales by adding replicas that share a JetStream durable
consumer (work splits automatically). The Rust engine scales by sharding the
Yellowstone subscription by program/account range and running multiple execution
consumers on the `exec.orders` group. Stores scale independently (read replicas,
ClickHouse shards, Neo4j causal cluster).
