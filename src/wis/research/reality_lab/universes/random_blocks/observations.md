# Observations — random_blocks

Measured from a real First Light session (replay-verified). Wallets discovered as non-vote fee payers of recent finalized blocks, then each wallet's own history observed.

### Universe B — random_blocks

* **Discovery**: Sample recent confirmed blocks (RPC getBlock); take fee payers of non-vote transactions.
* **Sample**: 5831 transactions · 5 parsed swaps · 7735 native transfers
* **Biases**: over-represents whatever is on-chain now (MEV/HFT bots); fee payers may be relayers/programs, not end users; point-in-time snapshot

| quantity | value | denominator |
|----------|------:|:--|
| P(BUG-001 \| swap) — token-to-token | **20.0%** ⚠ | 5 swaps |
| P(no trade \| swap) — swap ignorance | 20.0% ⚠ | 5 swaps |
| P(BUG-002 mechanics \| transfer) | **53.7%** | 7735 transfers |
| funding : trade event ratio | 1933.8 : 1 | 4 trades |
| multi-hop rate | 0.0% ⚠ | 5 swaps |
| zero-event transactions | 54.4% | 5831 txs |

* **Top types**: UNKNOWN 51.8%, SWAP 22.4%, TRANSFER 21.9%, INITIALIZE_ACCOUNT 2.2%, EXTEND_LOOKUP_TABLE 0.7%
* **Top swap shapes**: sol_paired_sell 40.0%, sol_paired_buy 40.0%, token_to_token 20.0%
* **Top sources**: RAYDIUM 60.0%, BYREAL 20.0%, JUPITER 20.0%

(⚠ = rate computed over a small denominator — treat as low-confidence.)

