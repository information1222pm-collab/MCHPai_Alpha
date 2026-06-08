# Segmentation findings — "active trader" decomposes

Phase 6 left a puzzle: `P(BUG-001 | active_traders)` ranged **28%–75%** across
fresh samples on *solid* denominators. That is not sampling noise — it is the
signature of a mixture. Phase 7 asked the unsupervised instruments (PCA +
Gaussian mixtures, BIC-selected) whether latent populations exist inside the
label. **They do.**

Analysis is over **captured raw sessions only** (no new observation). Wallets are
grouped by fee payer and kept only with ≥15 transactions (Statistics Rule 2).

## Result 1 — active_traders splits into ~6 behavioral classes

105 wallets. PCA(2D) explains 25% + 18% of variance. BIC drops monotonically from
k=1 (3139) to **k=6 (1548)** — decisive evidence of sub-structure. Silhouette
**0.28** (moderate: real but soft separation, not crisp islands).

| cluster | n | mean swaps | token-to-token | SOL-paired | Jupiter | reads as |
|--------:|--:|-----------:|---------------:|-----------:|--------:|----------|
| 2 | 36 | 72 | **0.79** | 0.06 | 0.98 | **Jupiter token-to-token routers** (~79% BUG-001) |
| 3 | 21 | 46 | **0.05** | **0.90** | 0.80 | **SOL-paired traders** (~5% BUG-001) |
| 0 | 12 | 14 | 0.42 | 0.53 | 0.43 | mixed, high mechanics |
| 1 | 9 | 51 | 0.52 | 0.00 | 0.78 | token-to-token, no native legs |
| 5 | 9 | 8 | 0.18 | 0.41 | 0.18 | low-activity, UNKNOWN-heavy |
| 4 | 18 | ~0 | 0.00 | 0.00 | 0.00 | **non-traders** (almost no swaps) |

**This explains the variance.** "Active traders" is ~34% Jupiter routers
(`P(BUG-001)≈79%`), ~20% SOL-paired traders (`P(BUG-001)≈5%`), and a long tail
including wallets that barely trade at all. A sample that happens to draw more
cluster-2 wallets reads ~75%; one heavy in cluster-3 reads ~28%. The mean
described nobody — exactly the warning that motivated this phase.

## Result 2 — the archetypes transcend the universe labels

Pooling all four observed universes (258 wallets) yields the **same** archetypes
(BIC best k=6, silhouette 0.13 — weaker, as expected for a more heterogeneous
pool):

* **Jupiter token-to-token routers** (n=43, t2t 0.83, jup 0.98)
* **SOL-paired traders** (n=45, sol 0.94)
* **High-swap, no-recognized-leg** wallets (n=32, swap 0.95, t2t/sol ≈ 0) —
  likely CLOB / aggregator / wrapped-SOL routes the parser leaves shapeless
* **Non-traders / transferers** (n=115 — the dominant pooled class)
* **Opaque / bot** wallets (n=13, UNKNOWN 0.91)

The human categories ("active traders", "pump.fun", "large wallets") are *not*
the categories reality clusters by. Behavior cuts across them.

See `figures/active_traders_pca.png`.

## Honest caveats

* **Soft, not crisp.** Silhouette 0.13–0.28 means clusters overlap; the structure
  is real (BIC) but partly continuous. Exact `k` is feature- and sample-dependent.
* **One session, ~100–260 wallets.** These are *hypotheses about reality's
  categories*, not established taxa. They must replicate on fresh samples before
  promotion (Phase 8 would re-run segmentation on new wallets and test cluster
  stability).
* **No fix, no label imposed.** We did not change `translate_helius`, and we did
  not name these classes in the taxonomy yet — they are candidates. Reality
  defines the populations; we only listened.

## Why this matters beyond BUG-001

`P(BUG-001)` was the first quantity we tried to condition on a universe. The
deeper lesson generalises: **any** wallet quantity (eventually `P(10x)`,
hold-time, risk) is likely a mixture over these latent behavioral classes.
Conditioning on the *discovered* population — not the human label — is the right
form of every future question.
