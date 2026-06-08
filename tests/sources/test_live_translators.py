"""The live-source translators (the valuable, testable core of each live feed)
turn provider payloads into the correct domain events. Verified against sample
payloads; live transports are separate and gated."""

from __future__ import annotations

from wis.domain.events import WalletBoughtToken, WalletFunded, WalletSoldToken
from wis.sources import translate_helius, translate_rpc, translate_yellowstone

T = 1_700_000_000  # block time seconds
AT = T * 1_000_000_000


def test_helius_swap_buy_and_sell_and_transfer() -> None:
    buy_tx = {
        "timestamp": T,
        "type": "SWAP",
        "feePayer": "alpha",
        "events": {"swap": {
            "nativeInput": {"account": "alpha", "amount": "1000000000"},
            "tokenOutputs": [{"mint": "GEM", "rawTokenAmount": {"tokenAmount": "1000000000", "decimals": 6}}],
        }},
    }
    [buy] = translate_helius(buy_tx)
    assert isinstance(buy, WalletBoughtToken)
    assert buy.wallet.value == "alpha" and buy.token.value == "GEM"
    assert buy.base.raw == 1_000_000_000 and buy.quote.raw == 1_000_000_000
    assert buy.occurred_at == AT

    sell_tx = {
        "timestamp": T,
        "type": "SWAP",
        "feePayer": "alpha",
        "events": {"swap": {
            "tokenInputs": [{"mint": "GEM", "rawTokenAmount": {"tokenAmount": "1000000000", "decimals": 6}}],
            "nativeOutput": {"account": "alpha", "amount": "3000000000"},
        }},
    }
    [sell] = translate_helius(sell_tx)
    assert isinstance(sell, WalletSoldToken)
    assert sell.quote.raw == 3_000_000_000

    transfer_tx = {
        "timestamp": T, "type": "TRANSFER", "feePayer": "alpha",
        "nativeTransfers": [{"fromUserAccount": "alpha", "toUserAccount": "bravo", "amount": "5000000000"}],
    }
    [funded] = translate_helius(transfer_tx)
    assert isinstance(funded, WalletFunded)
    assert funded.source.value == "alpha" and funded.target.value == "bravo"


def test_yellowstone_swap_and_transfer() -> None:
    [buy] = translate_yellowstone({
        "block_time": T, "kind": "swap", "wallet": "alpha", "side": "buy",
        "token": {"mint": "GEM", "amount": "1000000000", "decimals": 6}, "sol_lamports": "1000000000",
    })
    assert isinstance(buy, WalletBoughtToken) and buy.base.raw == 1_000_000_000

    [funded] = translate_yellowstone({
        "block_time": T, "kind": "transfer", "source": "alpha", "target": "bravo", "lamports": "5000000000",
    })
    assert isinstance(funded, WalletFunded)


def test_rpc_infers_buy_and_sell_from_balance_deltas() -> None:
    buy_tx = {
        "blockTime": T,
        "transaction": {"message": {"accountKeys": ["alpha"]}},
        "meta": {
            "preBalances": [10_000_000_000], "postBalances": [9_000_000_000],
            "preTokenBalances": [],
            "postTokenBalances": [{"owner": "alpha", "mint": "GEM", "uiTokenAmount": {"amount": "1000000000", "decimals": 6}}],
        },
    }
    [buy] = translate_rpc(buy_tx)
    assert isinstance(buy, WalletBoughtToken)
    assert buy.base.raw == 1_000_000_000 and buy.quote.raw == 1_000_000_000

    sell_tx = {
        "blockTime": T,
        "transaction": {"message": {"accountKeys": ["alpha"]}},
        "meta": {
            "preBalances": [9_000_000_000], "postBalances": [12_000_000_000],
            "preTokenBalances": [{"owner": "alpha", "mint": "GEM", "uiTokenAmount": {"amount": "1000000000", "decimals": 6}}],
            "postTokenBalances": [{"owner": "alpha", "mint": "GEM", "uiTokenAmount": {"amount": "0", "decimals": 6}}],
        },
    }
    [sell] = translate_rpc(sell_tx)
    assert isinstance(sell, WalletSoldToken)
    assert sell.base.raw == 1_000_000_000 and sell.quote.raw == 3_000_000_000


def test_rpc_ignores_non_swaps() -> None:
    assert translate_rpc({"blockTime": None}) == []
    assert translate_rpc({
        "blockTime": T, "transaction": {"message": {"accountKeys": ["alpha"]}}, "meta": {},
    }) == []
