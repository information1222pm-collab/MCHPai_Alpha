# taxonomy_validation_lab

Determine whether a candidate population *exists* — before anyone names it.

Phase 7 found clusters. This lab asks: are they real, or artifacts of one
session, one feature set, one clustering? It treats the clusters as anonymous
candidates (`Cluster0`, `Cluster1`, …) and grants a name only when reality
reproduces the structure.

## The two tests

* **Existence (algorithm-free).** Is the defining axis (`frac_token_to_token`)
  genuinely bimodal among swap-active wallets, and does that bimodality reproduce
  in independent samples? `stability.bimodality`.
* **Stability (resampling).** How often do a cluster's members re-cluster
  together across bootstraps? `stability.consensus_matrix` /
  `cluster_stabilities`. ≥0.6 reproduces; <0.4 is an artifact.

```bash
python -m wis.research.taxonomy_validation_lab.validate \
    --raw active_traders=sessions/reality_100/sample.jsonl \
    --raw pumpfun=sessions/pumpfun/raw_session.jsonl \
    --out-dir sessions/validation
```

## What it found (see `findings.md`)

* **5 of 6 candidate clusters survive resampling** (the router and SOL-paired
  clusters most robustly); one small cluster dissolves — it was noise.
* The token-to-token split is **strongly bimodal in active_traders** (separation
  0.73) but **cannot yet be replicated on fresh independent samples** — the other
  universes have too few swap-active wallets.
* **No names earned.** Internal stability ≠ fresh-sample replication. Until the
  structure recurs in genuinely fresh active-trader sessions, every cluster keeps
  its anonymous id.

## Discipline

Existence precedes naming. Behavior precedes stories. Nature gives gradients, not
islands — soft separation is expected; we measure *stability*, not crispness. No
fixes, no prediction, no taxonomy classes. Names are privileges granted by
replication.
