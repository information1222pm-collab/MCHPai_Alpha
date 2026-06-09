"""Regression fixtures captured from REAL Helius payloads (First Light #1).

These now pin the translator's *fixed* behavior (BUG-001 / BUG-002 addressed,
behind these regression tests built from the real payloads that revealed them).
See `reality_lab/bug_journal.md`."""

from __future__ import annotations

import json
from pathlib import Path

from wis.sources.helius_source import translate_helius

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "helius"


def _load(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text())


def test_token_to_token_quote_leg_now_priced() -> None:
    # BUG-001 FIXED: a real USDC→token Jupiter swap is now a BUY priced in USDC.
    tx = _load("token_to_token_swap.json")
    events = translate_helius(tx)
    assert [e.EVENT_TYPE for e in events] == ["WalletBoughtToken"]
    buy = events[0]
    assert buy.quote_mint == "USDC"
    # input USDC (83.608407) → output token; the token is the position acquired.
    assert buy.quote.raw == 83_608_407 and buy.quote.decimals == 6
    assert buy.token.value == "27G8MtK7VtTcCHkpASjSDdkWWYfoqT6ggEuKidVJidD4"


def test_swap_mechanics_transfers_now_filtered() -> None:
    # BUG-002 (partial): rent (2,039,280) and dust are dropped; only the larger
    # native movement survives. This tx has no parsed events.swap, so the residual
    # AMM payment still leaks as funding — an honest, journaled limitation.
    tx = _load("swap_only_native_transfers.json")
    events = translate_helius(tx)
    kinds = [e.EVENT_TYPE for e in events]
    # The two ATA-rent transfers (deposit + refund) are gone; 3 → 1.
    assert kinds.count("WalletFunded") == 1
    assert all(k == "WalletFunded" for k in kinds)
