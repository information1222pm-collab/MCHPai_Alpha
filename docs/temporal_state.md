# Temporal State — Recording the Universe as Sequences

> Phase 2 doctrine: store **movies, not statistics**. Every entity is recorded as
> `state(t)` so future temporal models inherit ordered trajectories for free.

## What we record

| Sequence            | Reducer (`libraries/.../timelines`) | Sink (ClickHouse)   | Feeds (future)            |
|---------------------|-------------------------------------|---------------------|---------------------------|
| `token_state(t)`    | snapshot-engine + `build_trajectory`| `snapshots`         | Temporal Fusion Transformers |
| `wallet_state(t)`   | `WalletStateReducer`                | `wallet_states`     | Wallet transformers       |
| `creator_state(t)`  | `CreatorStateReducer`               | `creator_states`    | Creator embeddings        |
| `graph(t)`          | `GraphStateReducer`                 | `graph_states`      | Temporal GNNs             |

All sinks are **append-only** and ordered by `(entity, ts)` with a monotonic
`seq` — never overwritten.

## Token trajectory

A token's life is the ordered sequence `birth → growth → viral → distribution →
death`. `snapshot-engine` emits phase-labeled snapshots; `build_trajectory`
collapses them into a `TokenTrajectory` (the matrix form a TFT consumes) and
extracts the phase-transition path.

## Wallet movies

`WalletStateReducer` maintains live FIFO lots and, after every swap, emits a
`WalletState`: realized PnL, open exposure, position concentration (Herfindahl),
conviction, scaling, cumulative volume. Replaying a wallet's swaps through the
reducer **deterministically rebuilds its entire trajectory** — verified by tests.

## Creator evolution

Creators change. `CreatorStateReducer` records the running track record
(`launches_so_far`, `rug_rate`, `best_multiple_so_far`, `alive_count`) at each
launch/resolution, so we can later learn creator *trajectories* and embed them.

## Dynamic graph

Most graph stores are static; ours is temporal. `GraphStateReducer` snapshots
node/edge/cluster counts, density, and edge growth on an interval, so a temporal
GNN can learn how structure *changes* (clusters forming, funding trees growing),
not just its current shape.

## Determinism & replay

Reducers are **pure** (no I/O). The immutable `event_log` (every envelope) plus
durable Redis/NATS streams mean any `state(t)` can be rebuilt by replaying events
through the reducers — essential for backtesting, debugging, and adding new state
dimensions retroactively.

## The milestone, not the model

We are deliberately *not* training transformers yet. The Phase-2 milestone is
**data**: 1,000,000 snapshots → 10,000 tokens → 100,000 tokens. Progress is
tracked live (`GET /stats`, Redis `stats:*` counters). Once ~50k+ tokens and
millions of snapshots are recorded, the temporal models become almost inevitable.
