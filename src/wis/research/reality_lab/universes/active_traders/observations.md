# Observations — active_traders

Measured from the Reality-100 session archive (real data, on disk; the 143 MB raw sample is git-ignored, representative fixtures are committed).

### Universe A — active_traders

* **Discovery**: Fee payers of recent transactions on six DEX programs, then each wallet's recent history.
* **Sample**: 9793 transactions
* **Biases**: skews to active DEX traders; Jupiter over-represented (used in discovery); single session; not time-diversified

| quantity | value |
|----------|------:|
| P(BUG-001 \| swap) — token-to-token | **59.1%** |
| P(no trade \| swap) — swap ignorance | 73.1% |
| P(BUG-002 mechanics \| transfer) | **72.0%** |
| funding : trade event ratio | 13.4 : 1 |
| multi-hop rate | 1.3% |
| zero-event transactions | 25.6% |

* **Top types**: SWAP 59.2%, TRANSFER 21.6%, UNKNOWN 9.9%, INITIALIZE_ACCOUNT 3.9%, TOKEN_MINT 2.6%
* **Top swap shapes**: token_to_token 59.1%, sol_paired_sell 14.9%, sol_paired_buy 11.8%, native_only 10.6%, empty 3.5%
* **Top sources**: JUPITER 93.2%, RAYDIUM 4.7%, BYREAL 1.3%, METEORA 0.8%

Source detail and methodology: [`../../distributions.md`](../../distributions.md).
