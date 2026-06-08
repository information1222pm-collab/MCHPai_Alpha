# Universes — the replication ledger

One sample can lie. The first wallet said `P(BUG-001) ≈ 99%`; 100 wallets said
`59%`. Replication across *different* populations is how we learn whether a
finding is a property of reality or an artifact of sampling.

Each universe is a population with a documented **discovery method** and honest
**biases**. The same measurement instrument
([`../replicate.py`](../replicate.py)) is applied to each, so distributions are
directly comparable. **Observations are recorded only from real data** — empty
is acceptable; invented is not (Rule 0, [`SCIENTIFIC_METHOD.md`](../../../../../../docs/SCIENTIFIC_METHOD.md)).

| # | universe | status | P(BUG-001) | P(BUG-002 mech) | funding:trade | multi-hop |
|---|----------|--------|-----------:|----------------:|--------------:|----------:|
| A | [active_traders](active_traders/observations.md) | observed | 59.1% | 72.0% | 13.4:1 | 1.3% |
| B | [random_blocks](random_blocks/observations.md) | awaiting First Light | — | — | — | — |
| C | [random_wallets](random_wallets/observations.md) | awaiting First Light | — | — | — | — |
| D | [high_pnl](high_pnl/observations.md) | requires characterization | — | — | — | — |
| E | [pumpfun](pumpfun/observations.md) | awaiting First Light | — | — | — | — |
| F | [old_wallets](old_wallets/observations.md) | requires characterization | — | — | — | — |
| G | [large_wallets](large_wallets/observations.md) | requires characterization | — | — | — | — |
| H | [dormant_wallets](dormant_wallets/observations.md) | requires characterization | — | — | — | — |

A `—` is not a placeholder for a number we will guess later. It is the honest
record that **we have not observed this universe yet.** The telescope is built;
First Light for B–H awaits a working credential.

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
