# Universes — the replication ledger

One sample can lie. The first wallet said `P(BUG-001) ≈ 99%`; 100 wallets said
`59%`. Replication across *different* populations is how we learn whether a
finding is a property of reality or an artifact of sampling.

Each universe is a population with a documented **discovery method** and honest
**biases**. The same measurement instrument
([`../replicate.py`](../replicate.py)) is applied to each, so distributions are
directly comparable. **Observations are recorded only from real data** — empty
is acceptable; invented is not (Rule 0, [`SCIENTIFIC_METHOD.md`](../../../../../../docs/SCIENTIFIC_METHOD.md)).

| # | universe | status | P(BUG-001) | P(BUG-002 mech) | funding:trade | swaps (denom) |
|---|----------|--------|-----------:|----------------:|--------------:|----:|
| A | [active_traders](active_traders/observations.md) | observed (×5) | **46% [21–71%]** | ~50% | 13.4:1 | 5 trials |
| B | [random_blocks](random_blocks/observations.md) | observed (×1) | 20% ⚠ | 53.7% | 1934:1 | 1 session |
| C | [random_wallets](random_wallets/observations.md) | awaiting First Light | — | — | — | — |
| D | [high_pnl](high_pnl/observations.md) | requires characterization | — | — | — | — |
| E | [pumpfun](pumpfun/observations.md) | observed (×5) | **4% [0–10%]** | ~29% | 177:1 | 5 trials |
| F | [old_wallets](old_wallets/observations.md) | requires characterization | — | — | — | — |
| G | [large_wallets](large_wallets/observations.md) | observed (×2) | **33% [0–100%]** ⚠ | ~64% | 8.2:1 | 2 trials |
| H | [dormant_wallets](dormant_wallets/observations.md) | requires characterization | — | — | — | — |

P(BUG-001) for observed universes is now the **across-trial mean with 95% CI**
(see [`../reproducibility.md`](../reproducibility.md)); single-session figures are
in each `observations.md`. `⚠` = small denominator or too few trials. A `—` is
the honest record that **we have not observed this universe yet.**

## Findings — replication then reproducibility

**1. `P(BUG-001)` is a distribution over universes (replication, Phase 5).**
Single sessions: large_wallets 8.7% · pump.fun 15.8% · active_traders 59.1%.
There is no single `P(BUG-001)`; only `P(BUG-001 | universe)`.

**2. Even within a universe, `P(BUG-001)` does not reproduce tightly
(reproducibility, Phase 6).** Five fresh active-trader samples ranged **28%–75%**
on solid denominators — real heterogeneity, not noise. The honest estimate is
`46% [21–71%]`, not `59%`. Pump.fun is reproducibly **low** (`4% [0–10%]`);
large_wallets is **uninformative** on 2 trials (`CI [0–100%]`).

**3. `P(BUG-002)` reproduces well and orders the universes** — pump.fun ~29% <
active ~50% < large ~64%, with tight intervals on large denominators. The
*ordering* is the robust, reproducible fact; "funding edges are mostly plumbing"
holds everywhere (34–72%). The funding:trade ratio swings 8:1 → ~1900:1.

**Verdict:** some quantities reproduce (P(BUG-002), the universe ordering); the
magnitude of P(BUG-001) does not, at this sample size. We report the wide
interval rather than a false point.

**What remains unknown.** C (random_wallets), D (high_pnl), F (old_wallets), H
(dormant_wallets) have not been observed. C overlaps B by construction; D/F/H need
a two-stage characterization pass (rank by observed PnL / page to genesis / detect
inactivity). Until run, their distributions are **unknown** — not estimated.

## How a universe gets populated

1. Discover wallets via the universe's method (registry + parsers in
   [`__init__.py`](__init__.py)).
2. Observe them through the existing pipeline (`reality_lab.observe`), capturing
   raw + events and proving `live_digest == replay_digest`.
3. Measure with `replicate.measure(...)`, render with `replicate.render_markdown`,
   and write the result into the universe's `observations.md`.
4. Capture a few representative real payloads into the universe's `fixtures/` as
   institutional memory.

The instrument never changes between universes. Only reality does.
