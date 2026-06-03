# Database Design

Three operational stores with clear, non-overlapping responsibilities, plus
Redis (cache) and MinIO (artifacts).

## PostgreSQL — the truth database

Source of record for entities and money. Strong consistency, transactions.
Schema: `infrastructure/postgres/init.sql`.

Core tables: `tokens`, `wallets`, `wallet_profiles`, `trades`, `wallet_scores`,
`clusters`, `cluster_members`, `predictions`, `positions`, `fills`,
`leaderboard_snapshots`.

Principles: every entity has a stable natural key (mint, address); scores and
profiles are 1:1 snapshots (history goes to ClickHouse); money tables
(`positions`, `fills`) are append-friendly and auditable.

## ClickHouse — time-series & analytics

The firehose and the training substrate. Append-only, partitioned by day, TTL'd.
Schema: `infrastructure/clickhouse/init.sql`.

Tables: `trades` (every swap), `token_snapshots`, `feature_vectors` (Map-typed
feature sets for training/serving), `attention` (entropy/R0/mass telemetry).

Why separate from Postgres: memecoin swaps are millions/day; columnar scans for
feature pulls and backtests would crush an OLTP DB.

## Neo4j — graph intelligence

The relationship brain. Schema/bootstrap: `infrastructure/neo4j/init.cypher`.

Nodes: `Wallet`, `Token`, `Cluster`. Edges: `FUNDED`, `TRANSFERRED`, `BOUGHT`,
`CO_BOUGHT`, `IN_CLUSTER`. GDS provides Louvain community detection and
shared-funding ancestry queries. See [graph_intelligence](graph_intelligence.md).

## Redis — hot cache & shared state

Sub-millisecond state shared across the Rust and Python tiers:
`token:meta:{mint}`, `wallet:hot:{address}`, `score:wallet:{address}`,
`pred:{mint}`, leaderboards (ZSETs), and the kill-switch `exec:paused`. Also the
low-latency bus: `raw.swaps`, `exec.orders`, `exec.fills` streams.

## MinIO — feature store & model registry

S3-compatible. Buckets: `features`, `models`, `datasets`, `backtests`. Models are
artifact + JSON manifest; the prediction-engine loads the latest published
manifest. Versioned so promotions/rollbacks are trivial.

## Data lifecycle

`event → Redis (hot) → Postgres (truth) + ClickHouse (history) → MinIO (training
sets) → models → back to serving`. Nothing authoritative lives only in cache.
