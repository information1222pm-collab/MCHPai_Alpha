# Feature Engineering

The `feature-engine` is a **feature factory** designed to grow to 1,000+
features. Features are organized into independent *families* (plugins); adding a
family adds features platform-wide without touching the core loop.

## Families (`services/feature-engine/feature_engine/families.py`)

| Family      | Examples                                            | Backed by               |
|-------------|-----------------------------------------------------|-------------------------|
| `creator`   | prior tokens, rug rate, success rate                | Postgres history        |
| `liquidity` | liquidity_sol, log liquidity, LP burned             | snapshots               |
| `spread`    | flow imbalance, buy/sell ratio, holder Gini         | `indicators`            |
| `entropy`   | buyer entropy, distinct buyers, KL regime shift     | `entropy` lib           |
| `attention` | R0, token mass, attention, velocity, luminosity     | `epidemiology`+`astronomy`|
| `ecology`   | wallet diversity, carrying capacity                 | `ecology` lib           |

Each family is `(context: dict) -> dict[str, float]`; `compute_all` namespaces
outputs as `family.feature`. The first-class **domain sciences** (entropy,
epidemiology, ecology, astronomy) are wired directly into production features —
not just research.

## Output

Feature vectors are written to:

* **ClickHouse** `feature_vectors` (Map-typed) — for training & analysis.
* **Redis** `feat:vec:{mint}` (TTL) — for low-latency serving to the predictor.

This dual-write is the classic **online/offline feature store** split: the same
features serve live decisions and train models, eliminating train/serve skew.

## Discipline

* **No leakage**: a feature at time *t* uses only data ≤ *t*. Labels are forward
  outcomes; training uses walk-forward splits.
* **Versioned feature sets**: the `feature_set` column lets us evolve the catalog
  while keeping historical training sets reproducible.
* **Cheap first**: structural/deterministic features (safety flags) gate before
  expensive ones; the hot path reads cached vectors, never recomputes.

## Roadmap to 1,000+ features

Add families for: temporal (time-of-day, age buckets), microstructure (sandwich
detection, sniper density), cross-token (sector rotation), wallet-relative
(distance from a wallet's niche — see `astronomy.gravitational_pull`), and
graph-derived embeddings (from the GNN).
