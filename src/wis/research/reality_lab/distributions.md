# Reality Distributions

> Measure reality. Do not fix it.

Quantified prevalence of observed phenomena. This is the empirical record that
tells us **which problems matter and how much** — before any translator change.
Numbers here set priorities; fixes wait for them.

The classifiers that produce these counts live in
[`taxonomy.py`](taxonomy.py); the named classes are catalogued in
[`taxonomy.md`](taxonomy.md).

---

## Session: Reality-100 — 2026-06-08

**Sample.** 100 wallets · **9,793 transactions** · Helius Enhanced Transactions
(mainnet).

**Sampling method & bias (stated honestly).** Wallets were discovered as the fee
payers of recent transactions on six programs (Jupiter, Raydium, pump.fun, Orca,
Meteora, Token program), then each wallet's own recent history (≤100 tx) was
observed. This skews toward **active DEX traders**, and including the Jupiter
program in discovery likely **inflates Jupiter's share**. Treat percentages as
representative of *active trading wallets*, not all of Solana.

---

### Transaction type distribution (n = 9,793)

| type | count | share |
|------|------:|------:|
| SWAP | 5,794 | 59.2% |
| TRANSFER | 2,115 | 21.6% |
| UNKNOWN | 974 | 9.9% |
| INITIALIZE_ACCOUNT | 386 | 3.9% |
| TOKEN_MINT | 254 | 2.6% |
| CLOSE_ACCOUNT | 244 | 2.5% |
| COMPRESSED_NFT_MINT | 14 | 0.1% |
| other (NFT bids, SWAP_EXACT_OUT, …) | 12 | 0.1% |

### Swap shape distribution

Of the 5,794 `SWAP`-typed transactions, **4,275 (73.8%) carry a parsed
`events.swap`**; the other **1,519 (26.2%) have no swap event at all**
(`NOT_A_SWAP`). Among the 4,275 with a swap event:

| shape | count | share | translated today? |
|-------|------:|------:|:--:|
| token_to_token | 2,527 | 59.1% | ✗ (BUG-001) |
| sol_paired_sell | 638 | 14.9% | ✓ |
| sol_paired_buy | 505 | 11.8% | ✓ |
| native_only | 455 | 10.6% | ✗ |
| empty | 150 | 3.5% | ✗ |

→ Only **26.7%** of parsed swaps are SOL-paired (the shape the translator
captures). **~73% of parsed swaps yield no trade event.**

### Swap routing source

| source | share |
|--------|------:|
| JUPITER | 93.2% |
| RAYDIUM | 4.7% |
| BYREAL | 1.3% |
| METEORA | 0.8% |

Jupiter overwhelmingly dominates routing (with the discovery caveat above).
`BYREAL` is a previously-unseen source — logged to the taxonomy watchlist.

### Route hops (of parsed swaps)

| hops | share |
|-----:|------:|
| 0 | 82.7% |
| 1 | 16.1% |
| 2 | 0.6% |
| ≥3 | 0.6% |

**Multi-hop is rare: 1.3%.** A real, assumption-correcting result — complex
multi-hop routing is *not* a priority. Most trades are 0–1 hop.

### Native transfer classification (n = 15,345 SOL movements)

| class | share | meaning |
|-------|------:|---------|
| dust (<0.0001 SOL) | 51.6% | fees / tips |
| ata_rent (=2,039,280) | 20.3% | token-account rent deposit/refund |
| small (<0.01 SOL) | 16.5% | mostly mechanics |
| medium (<1 SOL) | 9.8% | mixed |
| large (≥1 SOL) | 1.7% | candidate real flows |

**Counterparty:** 100% of native-transfer counterparties were **non-peer** (not
in the observed wallet set) — i.e. vaults/programs, not wallet-to-wallet funding.
At least **72%** (dust + ata_rent) is pure swap mechanics.

### Event ignorance

| metric | value |
|--------|------:|
| transactions producing **zero** domain events | 25.6% |
| swaps producing a **trade** event | 26.9% |
| total trade events | 1,149 |
| total funding events | 15,345 |
| **funding : trade event ratio** | **13.4 : 1** |

---

## Headline findings (priorities, not fixes)

1. **BUG-001 is ~59% of parsed swaps, not ~99%.** The first single-wallet sample
   was unrepresentative. Token-to-token is the largest single gap, but SOL-paired
   trades (26.7%) are a meaningful, already-captured slice. *This correction is
   the entire reason we observe before fixing.*
2. **BUG-002 is severe and quantified:** funding events outnumber trade events
   **~13:1**, and ≥72% of those are dust/rent mechanics to non-peer vaults. The
   funding graph would be dominated by artifacts.
3. **Multi-hop routing is negligible (1.3%)** — do not build for it yet.
4. **Jupiter is the dominant venue** (with sampling caveat); Raydium a distant
   second; `BYREAL` newly observed.
5. **~26% of `SWAP`-typed transactions carry no `events.swap`** — a separate
   phenomenon (`NOT_A_SWAP` within type SWAP) worth its own investigation.

No fixes applied. Re-run on a fresh sample to test stability before acting.
