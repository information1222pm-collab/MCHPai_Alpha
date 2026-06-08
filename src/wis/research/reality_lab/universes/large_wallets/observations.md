# Observations — large_wallets

Two-stage discovery: candidates from DEX-program fee payers, then filtered to SOL balance >= 10 (top holder 5129 SOL). Real First Light session, replay-verified: `live_digest == replay_digest` = True.

### Universe G — large_wallets

* **Discovery**: Two-stage: discover candidates, getBalance, keep top holders by SOL balance.
* **Sample**: 3505 transactions · 1063 parsed swaps · 5692 native transfers
* **Biases**: SOL balance != trading size (custody/treasury/CEX); large holders may rarely trade; ignores value held in tokens

| quantity | value | denominator |
|----------|------:|:--|
| P(BUG-001 \| swap) — token-to-token | **8.7%** | 1063 swaps |
| P(no trade \| swap) — swap ignorance | 35.1% | 1063 swaps |
| P(BUG-002 mechanics \| transfer) | **53.9%** | 5692 transfers |
| funding : trade event ratio | 8.2 : 1 | 690 trades |
| multi-hop rate | 0.1% | 1063 swaps |
| zero-event transactions | 25.2% | 3505 txs |

* **Top types**: SWAP 52.5%, TRANSFER 21.3%, UNKNOWN 17.0%, PLACE_MULTIPLE_POST_ONLY_ORDERS 2.9%, INITIALIZE_ACCOUNT 2.5%
* **Top swap shapes**: sol_paired_sell 34.2%, sol_paired_buy 30.6%, empty 20.8%, token_to_token 8.7%, native_only 5.6%
* **Top sources**: JUPITER 56.6%, RAYDIUM 36.9%, METEORA 6.1%, BYREAL 0.4%

