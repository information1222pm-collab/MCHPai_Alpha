"""The taxonomy classifiers — the measurement instrument — are pure and exercised
against the real captured fixtures plus synthetic shapes. They classify reality;
they never change translation."""

from __future__ import annotations

import json
from pathlib import Path

from wis.research.reality_lab.taxonomy import (
    ATA_RENT_LAMPORTS,
    NativeTransferClass,
    SwapShape,
    classify_native_transfer,
    classify_native_transfers,
    classify_swap_shape,
    is_multi_hop,
    route_hops,
    swap_source,
)

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "helius"


def _load(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text())


def test_swap_shape_token_to_token_fixture() -> None:
    tx = _load("token_to_token_swap.json")
    assert classify_swap_shape(tx) == SwapShape.TOKEN_TO_TOKEN
    assert swap_source(tx) == "JUPITER"


def test_swap_shape_synthetic_sol_paired() -> None:
    buy = {"events": {"swap": {"nativeInput": {"amount": "1"}, "tokenOutputs": [{"mint": "X"}]}}}
    sell = {"events": {"swap": {"tokenInputs": [{"mint": "X"}], "nativeOutput": {"amount": "1"}}}}
    assert classify_swap_shape(buy) == SwapShape.SOL_PAIRED_BUY
    assert classify_swap_shape(sell) == SwapShape.SOL_PAIRED_SELL


def test_swap_shape_not_a_swap() -> None:
    assert classify_swap_shape({"type": "TRANSFER"}) == SwapShape.NOT_A_SWAP
    assert classify_swap_shape({"events": {}}) == SwapShape.NOT_A_SWAP


def test_native_transfer_classes() -> None:
    assert classify_native_transfer(ATA_RENT_LAMPORTS, "a", "b") == NativeTransferClass.ATA_RENT
    assert classify_native_transfer(50_000, "a", "b") == NativeTransferClass.DUST
    assert classify_native_transfer(5_000_000, "a", "b") == NativeTransferClass.SMALL
    assert classify_native_transfer(500_000_000, "a", "b") == NativeTransferClass.MEDIUM
    assert classify_native_transfer(2_000_000_000, "a", "b") == NativeTransferClass.LARGE
    assert classify_native_transfer(123, "a", "a") == NativeTransferClass.SELF  # self before size


def test_native_transfers_on_real_fixture() -> None:
    tx = _load("swap_only_native_transfers.json")
    classes = classify_native_transfers(tx)
    # This real AMM swap includes the canonical ATA rent (deposit + refund).
    assert NativeTransferClass.ATA_RENT in classes
    assert len(classes) == len(tx["nativeTransfers"])


def test_route_hops_and_multi_hop() -> None:
    single = {"events": {"swap": {"innerSwaps": [{}]}}}
    multi = {"events": {"swap": {"innerSwaps": [{}, {}, {}]}}}
    assert route_hops(single) == 1 and not is_multi_hop(single)
    assert route_hops(multi) == 3 and is_multi_hop(multi)
    assert route_hops({"type": "TRANSFER"}) == 0
