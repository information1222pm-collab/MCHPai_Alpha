# Graph Intelligence

The `graph-engine` turns isolated wallets into a relationship graph and mines it
for **coordinated smart money** — the highest-signal entity in memecoin trading.

## The graph (Neo4j)

Nodes: `Wallet`, `Token`, `Cluster`. Edges:

* `(:Wallet)-[:BOUGHT {mint, ts, sol}]->(:Token)`
* `(:Wallet)-[:FUNDED {sol, ts}]->(:Wallet)` — bootstrapping ancestry
* `(:Wallet)-[:TRANSFERRED {amount, mint, ts}]->(:Wallet)`
* `(:Wallet)-[:CO_BOUGHT {mint, dt_seconds}]->(:Wallet)` — same mint within Δt
* `(:Wallet)-[:IN_CLUSTER]->(:Cluster {id, score})`

## Cluster detection pipeline

(`services/graph-engine/graph_engine/clustering.py`)

1. **Project** a weighted wallet graph in Neo4j GDS (weight = co-buys + funding +
   transfers).
2. **Louvain** community detection → candidate clusters.
3. **Validate coordination** — a cluster is only real if it passes:
   * **shared funding ancestry**: a common funder reached ≥60% of members within
     N hops (`shared_funder`); and/or
   * **co-buy lift**: observed co-buy rate ÷ random baseline ≫ 1.
4. **Score** (`cluster_score`): member alpha quality × coordination strength,
   plus a shared-funder bonus.

## Why this matters

A single profitable wallet can be luck. A *coordinated cluster* of profitable
wallets converging on a fresh mint, traceable to a shared funder, is the
strongest pre-pump precursor we have. The prediction-engine treats cluster
co-activation as a top feature in `buy_probability`.

## Detecting shared funding & historical co-buys

* **Shared funding**: variable-length `FUNDED*1..N` traversal to find common
  ancestors — catches wallets bankrolled from one source (insider rings, bundlers).
* **Historical co-buys**: `CO_BOUGHT` edges accumulate; lift over baseline
  distinguishes genuine coordination from popular-token coincidence.

## Scale

GDS runs server-side, so detection scales to millions of wallets. Real-time edge
writes are O(1); community detection runs on an interval (default 5 min) and on
demand around attention spikes.
