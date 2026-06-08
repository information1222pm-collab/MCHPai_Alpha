# Roadmap

A platform built for decades grows in deliberate phases. Each phase preserves the
two invariants — **replay determinism** and **point-in-time correctness** — so
nothing built later invalidates anything observed earlier.

## Phase 0 — The observatory core (shipped)

* Append-only event store, deterministic replay engine.
* `wallet_state(t)` with exact FIFO ledger; performance / timing / conviction /
  risk metrics; Wallet DNA.
* Declarative feature factory (leak-free, versioned, online/offline-consistent).
* Truth-weighted scoring with confidence shrinkage.
* `graph(t)`: funding trees + temporal co-buy edges; deterministic Louvain.
* Seven research labs (read-only). `Observatory` facade + read-only API.
* In-memory reference store; full pure-Python test suite; runnable demo.

## Phase 1 — Persist and scale out

* Production `EventStore` on **NATS JetStream**, archived to **MinIO**, verified
  against the in-memory oracle.
* Projection checkpoints in **PostgreSQL**; analytical trade/feature tables in
  **ClickHouse**; relationship graph mirrored to **Neo4j** (+ GDS).
* Hot `wallet_state(t)` and online features in **Redis**.
* Incremental projections (resume from a sequence cursor) and a backfill harness.
* **Rust** hot paths where latency demands it (ledger fold, co-buy edge updates).

## Phase 2 — Richer observation

* Token risk-label feed → activate `rug_exposure` / `scam_exposure` and
  scam/rug-aware DNA traits.
* Full price-path enrichment → trend-following vs mean-reversion tendency,
  smart-entry/exit, momentum preference, adaptability.
* Cluster evolution analytics: birth/merge/split detection across `cluster(t)`.
* Cross-sectional, percentile-normalized scores against the live population.

## Phase 3 — Foresight (only after the observatory is trusted)

* **Graph Neural Networks** over the funding/co-buy graph (already materialized).
* **Temporal Fusion Transformers** over sequence-preserving wallet frames.
* Reinforcement-learning research environments fed by replayable state.
* Calibrated, backtested forecasting — measured against reality first.

## Explicitly out of scope (for now, by charter)

Execution, copy trading, Jito/bundling, position sizing, and trading decisions.
The observatory's job is to *understand*. Anything that acts is a separate
system that may one day consume this intelligence — it will never live inside it.
