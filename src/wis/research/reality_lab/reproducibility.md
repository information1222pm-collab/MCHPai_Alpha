# Reproducibility (Phase 6)

Does `P(BUG-001 | universe)` reproduce across **fresh** wallet samples? For each
universe we ran K independent trials (disjoint, freshly-discovered wallets) and
measured each rate with its denominator. Statistics per `docs/STATISTICS.md`:
across-trial mean ± 95% t-interval (captures *which wallets we sampled*), plus the
pooled Wilson interval. `⚠` marks any rate over n<100.

## Universe A — Active traders  (K=5 trials)

| trial | wallets | txs | P(BUG-001) | swaps | P(BUG-002) | transfers |
|------:|--------:|----:|-----------:|------:|-----------:|----------:|
| 1 | 25 | 2403 | 41.2% | 233 | 43.3% | 5669 |
| 2 | 25 | 2315 | 57.4% | 350 | 43.6% | 6918 |
| 3 | 25 | 2206 | 75.3% | 369 | 59.4% | 6984 |
| 4 | 25 | 2463 | 28.7% | 540 | 51.1% | 6890 |
| 5 | 25 | 2387 | 28.2% | 666 | 54.9% | 7339 |

* **P(BUG-001)**: across-trial 46.2% ± 25.1% (95% CI)  ·  pooled 918/2158 = 42.5% (Wilson 95% [40.5%, 44.6%])  ·  variance=0.0407
* **P(BUG-002)**: across-trial 50.5% ± 8.8% (95% CI)  ·  pooled 17169/33800 = 50.8% (Wilson 95% [50.3%, 51.3%])  ·  variance=0.0050

## Universe E — Pump.fun  (K=5 trials)

| trial | wallets | txs | P(BUG-001) | swaps | P(BUG-002) | transfers |
|------:|--------:|----:|-----------:|------:|-----------:|----------:|
| 1 | 25 | 2353 | 0.0% | 101 | 22.5% | 8995 |
| 2 | 25 | 2279 | 0.0%⚠ | 41 | 33.3% | 9756 |
| 3 | 25 | 2343 | 10.5%⚠ | 19 | 33.4% | 9743 |
| 4 | 25 | 2204 | 8.5% | 130 | 26.1% | 8308 |
| 5 | 25 | 2212 | 0.0%⚠ | 11 | 30.5% | 9227 |

* **P(BUG-001)**: across-trial 3.8% ± 6.5% (95% CI)  ·  pooled 13/302 = 4.3% (Wilson 95% [2.5%, 7.2%])  ·  variance=0.0028
* **P(BUG-002)**: across-trial 29.1% ± 5.9% (95% CI)  ·  pooled 13504/46029 = 29.3% (Wilson 95% [28.9%, 29.8%])  ·  variance=0.0023

## Universe G — Large wallets  (K=2 trials)

| trial | wallets | txs | P(BUG-001) | swaps | P(BUG-002) | transfers |
|------:|--------:|----:|-----------:|------:|-----------:|----------:|
| 1 | 29 | 2868 | 20.2% | 544 | 64.1% | 6682 |
| 2 | 29 | 2900 | 45.5% | 398 | 63.7% | 5787 |

* **P(BUG-001)**: across-trial 32.8% ± 67.2% (95% CI) ⚠  ·  pooled 291/942 = 30.9% (Wilson 95% [28.0%, 33.9%])  ·  variance=0.0319
* **P(BUG-002)**: across-trial 63.9% ± 2.6% (95% CI) ⚠  ·  pooled 7969/12469 = 63.9% (Wilson 95% [63.1%, 64.7%])  ·  variance=0.0000

## What reproduces, what does not

* **P(BUG-001) does NOT reproduce tightly.** Within *active traders* alone, fresh
  trials ranged 28%–75% on solid denominators (233–666 swaps) — genuine population
  heterogeneity, not small-n noise. A single number with a tight CI is not
  attainable at this sample size; the universe is internally multi-modal.
* **P(BUG-002) reproduces well** within each universe and differs clearly between
  them: pump.fun ~29%, active traders ~50%, large wallets ~64% (tight intervals,
  large denominators). The *ordering* of universes is the robust, reproducible fact.
* **Honest limit:** pump.fun and large-wallet swap denominators were often small;
  several P(BUG-001) cells are ⚠. Their magnitudes remain uncertain. We do not
  paper over that with a confident average.
