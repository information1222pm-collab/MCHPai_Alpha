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

## Phase 1 — Persist and connect to reality (in progress)

Connect the observatory to durable storage without surrendering replay
determinism or point-in-time correctness. The in-memory store is the
**correctness oracle**; every adapter must reproduce bit-identical state. See
[`PERSISTENCE.md`](PERSISTENCE.md).

Done:
* Lossless, deterministic **event codec**; exact **world-digest** fingerprints;
  the store-agnostic **oracle-conformance harness** (`wis.conformance`).
* Durable **SQLite EventStore** — *verified in-sandbox*: passes conformance and
  replays bit-identically from disk after a process restart.
* **PostgreSQL** (system-of-record log) and **NATS JetStream + MinIO** (backbone
  + archive) EventStore adapters, plus **Redis** / **ClickHouse** / **Neo4j**
  derived-view sinks — implemented and wired to the same conformance harness via
  integration-gated tests (green the moment a live service is up).
* Pure projection→storage mapping (`projection_rows`), verified against the
  oracle in-process.

* **Source abstraction — reality enters through one door** (see
  [`SOURCES.md`](SOURCES.md)). `ArchiveSource` (the deterministic laboratory),
  `CSVSource` and `SyntheticSource` are verified in-sandbox; `HeliusSource`,
  `YellowstoneSource` and `RPCSource` have verified pure translators with gated
  live transports. Proven: all sources reconstruct identical `wallet_state(t)`.

Next:
* Run live conformance against the docker-compose stack; promote each adapter
  from "implemented" to "verified".
* Wire live source transports to real endpoints (Helius key, Yellowstone gRPC,
  RPC node); capture feeds into archives for deterministic replay.
* Incremental projections (resume from a sequence cursor) and a backfill harness.
* Construct and persist `WalletTrajectory` — the time-series of
  `wallet_state(t)` frames — as the substrate for future ML.
* **Rust** hot paths where latency demands it — only after correctness holds.

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
