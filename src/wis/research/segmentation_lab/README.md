# segmentation_lab

Discover the populations reality actually has — do not impose human ones.

"Active trader" was a label. The variance in `P(BUG-001)` (28%–75% across fresh
samples) was reality saying *there are latent classes here*. This lab places each
wallet in a behavioral space and lets unsupervised methods reveal the structure.

## Why now (and not before)

The earlier refusals stand: we did not build `wallet_alpha_score`, copy trading,
or prediction, because *we* wanted them. We permit unsupervised learning now
because **reality asked for it** — the question (find the hidden populations)
emerged from observation, not imagination.

## Instruments

* `features.py` — pure, dependency-free per-wallet behavioral features (swap-shape
  mix, venue mix, mechanics ratio, sizing, tempo). Scale-free where possible, so
  clusters reflect *behavior*, not volume.
* `cluster.py` — PCA, Gaussian mixtures (BIC-selected), hierarchical, HDBSCAN,
  silhouette, cluster profiling (`scikit-learn`, lazy).
* `segment.py` — runs the analysis over captured raw sessions and writes
  `findings.md` + a PCA plot. No network, no new observation.

```bash
python -m wis.research.segmentation_lab.segment \
    --raw active_traders=sessions/reality_100/sample.jsonl --out-dir sessions/segmentation
```

## What it found

See [`findings.md`](findings.md): "active trader" decomposes into ~6 behavioral
classes — Jupiter token-to-token routers (~79% BUG-001), SOL-paired traders (~5%),
non-traders, and bot/opaque wallets — and these archetypes recur across every
universe. The mixture explains the P(BUG-001) variance.

## Discipline

Exploratory, never predictive. No scores, no alpha, no trading, no
`WalletTrajectory`. Silhouette is reported honestly (the clusters are soft).
These are **candidate** populations — hypotheses to be replicated, not taxa to be
trusted. Reality defines the categories; the lab only listens.
