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
| A | [active_traders](active_traders/observations.md) | observed | 59.1% | 72.0% | 13.4:1 | ~4275 |
| B | [random_blocks](random_blocks/observations.md) | observed | 20.0% ⚠ | 53.7% | 1934:1 | 5 ⚠ |
| C | [random_wallets](random_wallets/observations.md) | awaiting First Light | — | — | — | — |
| D | [high_pnl](high_pnl/observations.md) | requires characterization | — | — | — | — |
| E | [pumpfun](pumpfun/observations.md) | observed | 15.8% | 34.4% | 177:1 | 158 |
| F | [old_wallets](old_wallets/observations.md) | requires characterization | — | — | — | — |
| G | [large_wallets](large_wallets/observations.md) | observed | 8.7% | 53.9% | 8.2:1 | 1063 |
| H | [dormant_wallets](dormant_wallets/observations.md) | requires characterization | — | — | — | — |

⚠ = computed over a small denominator (low confidence). A `—` is not a
placeholder for a number we will guess later — it is the honest record that **we
have not observed this universe yet.**

## Replication findings (as of 4 observed universes)

**`P(BUG-001)` is not a constant — it is a distribution over universes.** Measured
token-to-token share of parsed swaps:

* large_wallets **8.7%** · pump.fun **15.8%** · random_blocks **~20% ⚠** ·
  active_traders **59.1%**

The original "59%" was the **high end** (active DEX traders), not a property of
reality at large. This is the entire thesis of replication, confirmed: a single
universe's number generalizes badly.

**`P(BUG-002)` (transfer mechanics) is consistently high** (34%–72%) across every
universe — funding edges are mostly swap plumbing everywhere we look. The
funding:trade ratio, by contrast, swings enormously (8:1 for large traders →
~1900:1 for the random population that barely trades).

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
