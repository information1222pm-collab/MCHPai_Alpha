"""Tests for the universal swap parser (balance-delta extraction + DEX labeling)."""

from datetime import datetime, timezone

from mchpai_common.parsing import TokenBalance, TxContext, parse_transaction
from mchpai_common.parsing.program_ids import WSOL_MINT
from mchpai_common.schemas.common import Side
from mchpai_common.schemas.swap import Dex

PUMPFUN = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
RAYDIUM = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
JUPITER = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"
MINT = "MintAddr1111111111111111111111111111111111"
TS = datetime(2026, 1, 1, tzinfo=timezone.utc)
SOL = 1_000_000_000


def test_native_buy():
    ctx = TxContext(
        signature="sig1", slot=10, timestamp=TS, fee_payer="trader",
        program_ids=[PUMPFUN],
        pre_sol_lamports={"trader": 10 * SOL}, post_sol_lamports={"trader": 9 * SOL},
        pre_token_balances=[],
        post_token_balances=[TokenBalance("trader", MINT, 1000.0)],
        fee_lamports=0,
    )
    evs = parse_transaction(ctx)
    assert len(evs) == 1
    e = evs[0]
    assert e.side == Side.buy and e.dex == Dex.pumpfun
    assert e.sol_amount == 1.0 and e.token_amount == 1000.0
    assert abs(e.price - 0.001) < 1e-9
    assert e.wallet_address == "trader" and e.token_address == MINT


def test_native_sell():
    ctx = TxContext(
        signature="sig2", slot=11, timestamp=TS, fee_payer="trader",
        program_ids=[RAYDIUM],
        pre_sol_lamports={"trader": 9 * SOL}, post_sol_lamports={"trader": 11 * SOL},
        pre_token_balances=[TokenBalance("trader", MINT, 1000.0)],
        post_token_balances=[],
        fee_lamports=0,
    )
    evs = parse_transaction(ctx)
    assert len(evs) == 1 and evs[0].side == Side.sell
    assert evs[0].sol_amount == 2.0 and evs[0].dex == Dex.raydium_amm


def test_wsol_buy_counts_as_sol():
    ctx = TxContext(
        signature="sig3", slot=12, timestamp=TS, fee_payer="trader",
        program_ids=[PUMPFUN],
        pre_sol_lamports={"trader": 5 * SOL}, post_sol_lamports={"trader": 5 * SOL},
        pre_token_balances=[TokenBalance("trader", WSOL_MINT, 2.0)],
        post_token_balances=[
            TokenBalance("trader", WSOL_MINT, 0.0),
            TokenBalance("trader", MINT, 500.0),
        ],
        fee_lamports=0,
    )
    evs = parse_transaction(ctx)
    assert len(evs) == 1 and evs[0].side == Side.buy
    assert evs[0].sol_amount == 2.0 and evs[0].token_amount == 500.0


def test_marketcap_when_supply_known():
    ctx = TxContext(
        signature="sig4", slot=13, timestamp=TS, fee_payer="trader",
        program_ids=[PUMPFUN],
        pre_sol_lamports={"trader": 2 * SOL}, post_sol_lamports={"trader": 1 * SOL},
        pre_token_balances=[],
        post_token_balances=[TokenBalance("trader", MINT, 1000.0)],
        supply={MINT: 1_000_000_000.0},
    )
    e = parse_transaction(ctx)[0]
    assert e.market_cap == e.price * 1_000_000_000.0


def test_unknown_program_ignored():
    ctx = TxContext(
        signature="sig5", slot=14, timestamp=TS, fee_payer="trader",
        program_ids=["SomeRandomProgram1111111111111111111111111"],
        pre_sol_lamports={"trader": 2 * SOL}, post_sol_lamports={"trader": 1 * SOL},
        pre_token_balances=[],
        post_token_balances=[TokenBalance("trader", MINT, 1000.0)],
    )
    assert parse_transaction(ctx) == []


def test_jupiter_routes_to_concrete_dex():
    # Jupiter + Raydium present → label the concrete venue, not the router.
    ctx = TxContext(
        signature="sig6", slot=15, timestamp=TS, fee_payer="trader",
        program_ids=[JUPITER, RAYDIUM],
        pre_sol_lamports={"trader": 2 * SOL}, post_sol_lamports={"trader": 1 * SOL},
        pre_token_balances=[],
        post_token_balances=[TokenBalance("trader", MINT, 1000.0)],
    )
    assert parse_transaction(ctx)[0].dex == Dex.raydium_amm
