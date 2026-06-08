# Observations — pumpfun

Measured from a real First Light session (replay-verified: `live_digest == replay_digest` = True). Wallets discovered as fee payers of recent pump.fun program transactions.

### Universe E — pumpfun

* **Discovery**: Fee payers of recent pump.fun program transactions.
* **Sample**: 5780 transactions · 158 parsed swaps · 20763 native transfers
* **Biases**: memecoin-launch population: high churn, many one-shot wallets; bot-heavy; recent-activity survivorship

| quantity | value | denominator |
|----------|------:|:--|
| P(BUG-001 \| swap) — token-to-token | **15.8%** | 158 swaps |
| P(no trade \| swap) — swap ignorance | 25.9% | 158 swaps |
| P(BUG-002 mechanics \| transfer) | **34.4%** | 20763 transfers |
| funding : trade event ratio | 177.5 : 1 | 117 trades |
| multi-hop rate | 0.0% | 158 swaps |
| zero-event transactions | 14.3% | 5780 txs |

* **Top types**: SWAP 61.1%, TRANSFER 27.6%, UNKNOWN 9.6%, CREATE 0.7%, CLOSE_ACCOUNT 0.5%
* **Top swap shapes**: sol_paired_buy 54.4%, sol_paired_sell 19.6%, token_to_token 15.8%, empty 10.1%
* **Top sources**: JUPITER 100.0%

