# Reality Taxonomy

> Classify reality. Promote repeated patterns into classes. Do not fix.

A catalog of **phenomenon classes** — the recurring shapes reality presents.
These are not bugs and not fixes; they are the vocabulary an instrument earns by
observing. Classes that are coded live in [`taxonomy.py`](taxonomy.py); measured
prevalence lives in [`distributions.md`](distributions.md); the issues a class
implies live in [`bug_journal.md`](bug_journal.md).

A pattern is promoted to a named class once it is observed repeatedly and proves
common enough to matter. Reality becomes code; code becomes memory.

---

## SwapShape — how a swap's value legs are arranged

Coded: `wis.research.reality_lab.taxonomy.SwapShape`.

| class | definition | prevalence¹ | translated | issue |
|-------|------------|------------:|:--:|------|
| `SOL_PAIRED_BUY` | `nativeInput` + `tokenOutputs` | 11.8% | ✓ | — |
| `SOL_PAIRED_SELL` | `tokenInputs` + `nativeOutput` | 14.9% | ✓ | — |
| `TOKEN_TO_TOKEN` | token in + token out, no native leg | 59.1% | ✗ | BUG-001 |
| `NATIVE_ONLY` | native legs only, no token legs | 10.6% | ✗ | watch |
| `EMPTY` | a swap event with no recognizable legs | 3.5% | ✗ | watch |
| `NOT_A_SWAP` | `SWAP` type but no `events.swap` | 26.2%² | ✗ | watch |

¹ of 4,275 parsed swaps (Reality-100). ² of 5,794 `SWAP`-typed transactions.

## NativeTransferClass — what a SOL movement actually is

Coded: `wis.research.reality_lab.taxonomy.NativeTransferClass`.

| class | definition | prevalence³ | issue |
|-------|------------|------------:|------|
| `DUST` | < 0.0001 SOL | 51.6% | BUG-002 (fees/tips) |
| `ATA_RENT` | exactly 2,039,280 lamports | 20.3% | BUG-002 (rent/refund) |
| `SMALL` | < 0.01 SOL | 16.5% | BUG-002 (mechanics) |
| `MEDIUM` | < 1 SOL | 9.8% | mixed |
| `LARGE` | ≥ 1 SOL | 1.7% | candidate real flow |
| `SELF` | from == to | (rare) | mechanics |

³ of 15,345 native transfers (Reality-100). All counterparties were non-peer
(vault/program), not wallet-to-wallet.

## RoutingSource — the reported venue

Not yet an enum (sources are open-ended). Observed set, by prevalence:
`JUPITER` (93.2%), `RAYDIUM` (4.7%), `BYREAL` (1.3%), `METEORA` (0.8%).

---

## Watchlist — observed, not yet promoted

Patterns seen in the wild that may earn a class once prevalence/stability is
confirmed on more samples:

* **`BYREAL` source** — an unfamiliar router/aggregator. Capture a fixture.
* **`NOT_A_SWAP` within type SWAP** (26% of SWAP-typed) — swaps with no parsed
  `events.swap`. Investigate what shape the value takes (tokenTransfers only?).
* **`NATIVE_ONLY` swaps** (10.6%) — likely wrapped-SOL / SOL-leg-only routes.
* **`TOKEN_MINT` / `COMPRESSED_NFT_*`** — non-trade activity; classify as
  ignorable or as a separate (non-trading) behavior stream.

---

## Aspirational future classes (NOT yet observed/measured)

Named here only so we recognize them if reality shows them. **Do not implement
detection until observed and measured:**

`Token2022` · `PartialFill` · `RentRefund` (vs deposit) · `VaultTransfer` ·
`Sandwich` · `Bundle` · `WashTrade` · `JupiterInnerRoute`.

Detecting several of these (e.g. Token2022, sandwich, wash) requires data beyond
a single enhanced payload (mint program, block neighbors, cross-wallet
correlation). Logged as future instrument upgrades, not current work.

---

## How a class graduates

1. Observed repeatedly across a session.
2. Prevalence measured in `distributions.md`.
3. A real payload captured as a fixture (institutional memory).
4. Promoted to a coded class in `taxonomy.py` with a classifier + test.
5. Only *then*, if it implies a translator change, opened as a `bug_journal.md`
   entry — and fixed behind the replay-determinism contract.
