# The Feature Factory

> A machine that *generates features*, not a pile of hand-written features.

The Feature Factory is one of MCHPAI's strategic assets. Instead of writing
feature code, you **declare** features as data and a compiler turns them into a
single fast callable. The catalog scales 5 → 50 → 500 → 5,000+ features from
compact rules, and every feature is versioned, described, and introspectable.

## The pieces

```
FeatureSpec  ──┐
FeatureSpec  ──┤   build_default_catalog()  (rules → hundreds of specs)
   ...         │              │
FeatureSpec  ──┘              ▼
                       FeatureCompiler   (topo-sort the DAG, validate)
                              │
                  compute(ctx) / compute_sequence(rows)
                              ▼
                     {feature_name: value, ...}
```

* **`FeatureSpec`** — `name, transform, dependencies, window, params,
  normalization, description, version, tags`. Pure data.
* **transforms** — the verbs: `input, ratio, diff, sum, imbalance, rolling_mean/
  std/max/min/sum, zscore, rate_of_change, ewma, slope, acceleration, r0,
  entropy_of, gini_of`. Add one with `@register_transform` and it's available to
  every spec.
* **`FeatureCompiler`** — topologically sorts specs (a feature may depend on raw
  inputs *or* other features), detects cycles/missing deps, and compiles to
  `compute(context) -> dict`.
* **`FeatureContext`** — one entity-step (`inputs`) plus its ordered `history`
  (most recent last), so windowed transforms are correct and **causal**.

## Declarative generation (the scaling lever)

`catalog.py` declares rules, not features:

```python
BASE_METRICS = ["price_sol","volume_sol","buyers","sellers","net_flow_sol", ...]
WINDOWS      = [3, 5, 10, 20]
ROLLING      = ["rolling_mean","rolling_std","zscore","rate_of_change","slope", ...]
# → one spec per (metric × window × transform) + curated interactions
```

Today this expands to **435 features**. Adding one base metric or one transform
multiplies the catalog — without new glue code.

## Online / offline parity

The same compiled catalog runs:

* **online** in `feature-engine` (per-snapshot, bounded per-mint history) → Redis
  `feat:vec:{mint}` for serving;
* **offline** via `compute_sequence(rows)` over a token's full snapshot history →
  ClickHouse / training sets.

Because the specs are identical, there is **no train/serve skew**, and windowing
is causal in both paths (no look-ahead).

## Why this matters for decades

Features are the half-life-limited part of any quant system. Making them
*declarative data* means: experiments are diffs to a catalog, every feature is
self-describing, the same spec trains and serves, and the surface area scales
without scaling the code. New science (entropy, epidemiology, astronomy) enters
as new transforms and instantly becomes thousands of new features.
