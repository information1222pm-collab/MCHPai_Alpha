# Architecture

The Advanced Wallet Intelligence System is an **event-sourced, domain-driven**
platform. This document explains how the pieces fit and *why* — the decisions
that let it grow for decades.

## The spine: an append-only event log

Everything the system knows is derived from one ordered, immutable log of facts.
Every other store is a **derived view** that can be rebuilt by replaying the log.

```
                         ┌─────────────────────────────┐
   world facts  ───────► │      Event Store (log)      │ ◄── system conclusions
  (buys, sells,          │  gap-free global sequence   │     (derived events)
   funding, prices)      └──────────────┬──────────────┘
                                        │ replay (pure folds)
                ┌───────────────────────┼───────────────────────┐
                ▼                       ▼                        ▼
        WalletProjector          GraphProjector          (future projectors)
        wallet_state(t)             graph(t)              feature snapshots…
                │                       │
                ▼                       ▼
        FeatureCompiler          Louvain communities
        feature vectors          cluster(t)
                │                       │
                └──────────┬────────────┘
                           ▼
                    Scoring (truth-weighted)
                           ▼
                  Observatory facade ──► read-only API, research labs
```

Two clocks are tracked on every fact: **event time** (when it happened) and
**ingestion time** (when we learned it). Conflating them is the classic source
of look-ahead bias, so the envelope keeps them distinct and the point-in-time
read (`read_as_of`) uses ingestion time.

## Determinism as a first-class property

* **No wall-clock or RNG inside a fold.** Projections are pure functions of
  `(state, event)`.
* **Exact money.** Amounts are integers in their smallest unit; the trade ledger
  does FIFO lot matching in `fractions.Fraction`, so cost basis never drifts.
* **Stable ordering.** The store assigns a strictly monotonic, gap-free
  sequence; Louvain visits nodes in sorted order and breaks ties deterministically.

Result: the same log always reconstructs the same `wallet_state(t)` and
`graph(t)`. This is what makes the platform auditable and backtestable.

## Domain-driven boundaries

```
wis.domain        pure model, zero infra imports (the "what")
wis.eventsourcing the log, the envelope, the replay engine (the "when/order")
wis.projections   folds that turn events into read models (the "becomes")
wis.features      declarative features over read models (the "measure")
wis.scoring       compression of metrics into truth-weighted scores
wis.research      read-only analysis labs (no execution, ever)
wis.app           Observatory facade + HTTP surface
wis.infra         adapters to real datastores (depend on core, never reverse)
```

The dependency rule is strict and one-directional: **infrastructure depends on
the core; the core depends on nothing**. You can swap PostgreSQL for anything
without touching a line of intelligence code.

## Polyglot persistence (the right tool per job)

| Store | Role |
|-------|------|
| **NATS JetStream** | the durable, ordered event backbone |
| **MinIO** | replay-log archive, model/feature snapshots |
| **PostgreSQL** | system of record: registry, projection checkpoints |
| **ClickHouse** | analytical column store for billions of trade/feature rows |
| **Neo4j** | the wallet relationship graph at scale (+ GDS) |
| **Redis** | hot online cache: latest `wallet_state(t)` and online features |

Each production adapter implements a core protocol (e.g. `EventStore`) and is
verified against the `InMemoryEventStore` reference — the oracle of correctness.

## The feature factory

Features are **declared**, not hand-coded per call site. A `FeatureSpec` names a
feature `(name@version)`, its type, a description, tags, and one pure `extract`
function over a point-in-time `WalletFrame`. The `FeatureCompiler` runs every
spec against a single frame to produce a versioned `FeatureVector`.

* **Leak-free by construction** — a spec can only read a frame, and frames come
  only from point-in-time replays.
* **Online/offline consistent** — backfill and serving call the same `extract`
  on the same kind of frame, so values cannot diverge.
* **Built to scale to 5,000+ features** — add packs to `wis.features.library`;
  the machinery never changes.

## Scoring for truth

Scores are transparent, monotone functions of observed metrics, **shrunk toward
neutral by confidence** (`n / (n + k)`). There is no fitted "good trader" label
to chase. `wallet_alpha_score` is a documented weighted blend of expected-value,
consistency, timing, risk and conviction components. Graph-dependent scores are
`None` until `graph(t)` is supplied.

## Designed for what comes next

The read models and feature vectors are deliberately shaped to feed future
**Graph Neural Networks** (the co-buy/funding graph is already materialized),
**Temporal Fusion Transformers** (sequence-preserving frames), and reinforcement
learning — without re-architecting. Foresight is a later chapter; the observatory
is the foundation it stands on.
