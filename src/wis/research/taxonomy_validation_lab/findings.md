# Taxonomy validation — do the candidate populations exist?

Phase 7 found 6 candidate clusters. Phase 8 asks the prior question — **existence,
not identity** — and refuses to name anything until reality reproduces it.
Clusters keep anonymous ids. Analysis is over **captured raw sessions** (no new
observation); each universe is an independent sample.

## Test B — membership stability under resampling (decisive, key-free)

Pooled wallets (n=258), candidate partition k=6, **consensus co-association over
120 bootstraps** (how often a cluster's members re-cluster together):

| cluster | size | mean t2t | consensus stability | verdict |
|---------|-----:|---------:|--------------------:|---------|
| Cluster2 | 43 | 0.83 | **0.97** | REPRODUCES (stable) |
| Cluster5 | 13 | 0.05 | 0.87 | REPRODUCES (stable) |
| Cluster1 | 32 | 0.00 | 0.79 | REPRODUCES (stable) |
| Cluster3 | 45 | 0.06 | 0.79 | REPRODUCES (stable) |
| Cluster4 | 115 | 0.00 | 0.67 | REPRODUCES (stable) |
| Cluster0 | 10 | 0.44 | **0.33** | does NOT reproduce |

**5 of 6 candidate clusters survive resampling; one (the small mixed Cluster0,
n=10) dissolves** — it was an artifact. The high-token-to-token cluster
(`Cluster2`, stability 0.97) and the low-token-to-token cluster (`Cluster3`,
0.79) are the most robust. *Within this dataset*, the major populations are real,
not clustering accidents.

## Test A — does the defining split exist in independent samples?

Algorithm-free existence test: is `frac_token_to_token` bimodal among swap-active
wallets (≥5 swaps), in each independent universe?

| universe | swap-active n | bimodal? | modes | separation |
|----------|--------------:|:--------:|-------|-----------:|
| active_traders | 76 | **YES** | [0.27, 1.00] | 0.73 |
| large_wallets | 18 | no | [0.00, 0.19] | 0.19 |
| pump.fun | 3 | — (too few) | — | — |
| random_blocks | 0 | — (none) | — | — |

The split is **strongly bimodal where it can be measured** (active_traders:
well-separated router mode ≈1.0 and a mixed/SOL mode ≈0.27). But **the other
universes cannot serve as replication samples**: random_blocks has *no*
swap-active wallets, pump.fun only 3, and large_wallets is unimodal-low. So
cross-sample reproduction of the token-to-token split is **not yet confirmed** —
the available independent samples are behaviorally too different to test it.

See `figures/validation_modality.png`.

## Verdict (honest, incomplete)

* **Stable under resampling:** yes — 5/6 clusters reproduce; the router and
  SOL-paired clusters are robust. This is strong *internal* validity.
* **Replicated on fresh independent samples:** **not yet.** Bootstrap stability is
  not the same as fresh-sample replication. The gold-standard test — re-observe
  *fresh active-trader wallets* and check the bimodality + cluster profiles recur —
  has not been run (it needs a live credential).
* **Names earned:** **none.** Internal stability is necessary but not sufficient.
  Until the split reproduces in genuinely fresh active-trader sessions, every
  cluster keeps its anonymous id. Names are privileges granted by replication.

## Next (Phase 8 completion)

Collect ≥2 fresh active-trader sessions (new wallets) and re-run this lab. If
`Cluster2`/`Cluster3` reappear with consistent profiles and the t2t bimodality
holds, *then* — and only then — they may be promoted toward taxonomy. Until then:
existence is *supported, not established*.
