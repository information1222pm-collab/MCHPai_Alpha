# Reality Bug Journal

> Solve observed problems, not hypothetical ones.

This journal records issues **revealed by observing real wallets** — never
imagined ones. The translator (`wis.sources.helius_source.translate_helius`) is
held **fixed** until this journal justifies a change. Every fix lands behind the
replay-determinism contract, with a regression test built from the real payload
that revealed it.

A beautiful property makes this safe: `translate_helius()` is isolated from
`wallet_state(t)`. Reality can be ugly; truth stays stable. The First Light
session below produced **507 real events across 18 wallets**, and the archived
recording replayed to a **bit-identical digest**
(`a07907c72985a0a8…`) — replayability holds regardless of translation quality.

Each entry records: wallet · signature · raw payload · translation output ·
expected behavior · root cause · fix (deferred) · regression test.

---

## Session: First Light #1 — 2026-06-08

* **Source**: Helius Enhanced Transactions (mainnet).
* **Wallets observed**: 1 → 3 fee-payers (expanded to 18 via funding edges).
* **Transactions sampled**: ~1,300 across 13 discovered wallets.
* **Headline finding**: of 822 `SWAP` transactions, only **6 were SOL-paired**;
  ~99% are token-to-token (router) swaps the translator does not capture as
  trades. Most "translated" events were `WalletFunded` from incidental SOL
  transfers (fees/tips/rent), not real funding.
* **Replayability**: `live_digest == replay_digest` ✓ (proven on real data).

---

### BUG-001 — Token-to-token (router) swaps produce no trade events

| field | value |
|-------|-------|
| **wallet** | `AE861PyrYJXm2TuxiMc8Ecwo4YYgAHfcYum3GWpSRFe3` |
| **signature** | `3upjtDQnNBKh8uafXyRw8db9Nzzk1CN3wFi4bcaqidmHdHygUfgj9yjJYVACPkuEFYRZHy9TEFdrNzNHxinm4jTh` |
| **source** | JUPITER |
| **raw payload** | `tests/fixtures/helius/token_to_token_swap.json` |

**Raw shape (abridged).** `events.swap.nativeInput = null`,
`events.swap.nativeOutput = null`, `tokenInputs = [USDC 83.608407]`,
`tokenOutputs = [<mint> 24.986035]`.

**Translation output.** `translate_helius(tx) == []` — zero domain events.

**Expected behavior (eventual).** A token-to-token swap is economically a SELL of
the input token and a BUY of the output token. The observatory should represent
it — most naturally by pricing both legs in a common quote (the quote token, or a
SOL-equivalent via `innerSwaps`), or by recording two trades against the quote
asset. Exact modeling is **deferred** until the journal shows which shapes
dominate.

**Root cause.** `translate_helius` only handles SOL-paired swaps
(`nativeInput + tokenOutputs` → BUY, `tokenInputs + nativeOutput` → SELL). Real
volume is overwhelmingly routed token-to-token, where both native legs are null.

**Scale (revised by measurement — see distributions.md, Reality-100).** The
first single-wallet sample suggested ~99% (816/822); the 100-wallet sample of
9,793 transactions corrects this to **59.1% of parsed swaps** are token-to-token,
with ~73% of parsed swaps yielding no trade event and only 26.7% SOL-paired.
Still the single largest translator gap, but materially smaller than the first
sample implied — the correction is exactly why we measure before fixing.

**Fix.** DEFERRED. The 100-wallet distribution is in; before acting, re-run on a
fresh sample to confirm stability, and resolve how to price a token-to-token leg
(quote token vs SOL-equivalent). Multi-hop is negligible (1.3%) — do not build
for it. Pre-solving risks modeling the wrong thing.

**Regression test.** `tests/sources/test_reality_fixtures.py::test_token_to_token_currently_untranslated`
pins the current `[]` behavior; flip it when BUG-001 is addressed.

---

### BUG-002 — Incidental SOL transfers become spurious `WalletFunded` edges

| field | value |
|-------|-------|
| **wallet** | `7pZXp8WNiqfsxJJrvLLjS5bVKCWrCfSFQTefpLKwgJ8u` |
| **signature** | `C1RWXhUT4UAR8M8eSB2ddYDV8jhFZRkhin7cxcwEZqunyJr6jC5X5651pf9yUQ9qMvNFU6x1ATUFmzJQgE9LGAJ` |
| **source** | PUMP_AMM |
| **raw payload** | `tests/fixtures/helius/swap_only_native_transfers.json` |

**Raw shape.** A swap whose `events.swap` carries no native leg, but whose
`nativeTransfers` contains three SOL movements between the trader and an AMM
vault — including a `2039280` lamport (≈0.00204 SOL) **rent** deposit and its
**refund**.

**Translation output.** `['WalletFunded', 'WalletFunded', 'WalletFunded']` — the
fee/rent/vault transfers are recorded as *funding relationships*.

**Expected behavior (eventual).** `WalletFunded` should mean an actual funding
flow between participants, not swap mechanics (AMM vault payments, rent and its
refund, priority-fee/tip transfers). These should be filtered or classified, so
the funding graph reflects real lineage, not exchange plumbing. The SOL leg of
the swap itself should instead inform the **trade** (BUY cost), per BUG-001.

**Root cause.** `translate_helius` emits a `WalletFunded` for **every**
`nativeTransfers` entry, indiscriminately, with no notion of which transfers are
swap mechanics vs genuine peer funding.

**Impact (quantified — Reality-100).** Severe. Across 9,793 transactions, funding
events outnumber trade events **~13.4 : 1** (15,345 vs 1,149). Of native
transfers, **51.6% are dust** (fees/tips) and **20.3% are exactly the ATA rent**
(2,039,280 lamports) — ≥72% pure swap mechanics — and **100% of counterparties
were non-peer** (vaults/programs, not observed wallets). `graph(t)` would be
dominated by artifacts, not real lineage.

**Fix.** DEFERRED. The data now suggests a tractable filter (drop dust + ata_rent
+ non-peer counterparties), but confirm on a fresh sample first. See the
`NativeTransferClass` taxonomy. Gather more before acting.

**Regression test.** `tests/sources/test_reality_fixtures.py::test_swap_native_transfers_currently_funding`
pins the current behavior; revise when BUG-002 is addressed.

---

### Observed-but-not-yet-bugs (watchlist)

* `type` values seen that yield no events (expected for now): `INITIALIZE_ACCOUNT`,
  `CLOSE_ACCOUNT`, `UNKNOWN`, `COMPRESSED_NFT_MINT`. Recorded for completeness;
  no action — these are not trades.
* `nativeTransfers[].amount` arrives as an **int** here (not a string as in some
  docs). `translate_helius` already coerces with `int(...)`, so no issue — noted
  so a future "harden the parser" change does not assume a string.

---

## Protocol reminder

1. Observe (`python -m wis.research.reality_lab.observe`).
2. Capture raw + events; replay; **prove `live_digest == replay_digest`**.
3. For anything the translator mishandles, add an entry here with the real
   payload as a fixture.
4. Do **not** fix until the journal justifies it. Reality speaks first.
