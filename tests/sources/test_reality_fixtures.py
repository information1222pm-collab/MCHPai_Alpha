"""Regression fixtures captured from REAL Helius payloads (First Light #1).

These pin the translator's *current, observed* behavior on real-world shapes that
``bug_journal.md`` documents as gaps. They are intentionally asserting the
present (incomplete) behavior — when a bug is fixed, the matching assertion is
updated in the same commit, with the journal entry, so reality and tests move
together. Do NOT "fix" the translator to make these pass differently without a
journal entry justifying it."""

from __future__ import annotations

import json
from pathlib import Path

from wis.sources.helius_source import translate_helius

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "helius"


def _load(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text())


def test_token_to_token_currently_untranslated() -> None:
    # BUG-001: a real Jupiter token-to-token swap produces no trade events today.
    tx = _load("token_to_token_swap.json")
    assert tx["type"] == "SWAP" and tx["source"] == "JUPITER"
    sw = tx["events"]["swap"]
    assert sw["nativeInput"] is None and sw["nativeOutput"] is None
    assert sw["tokenInputs"] and sw["tokenOutputs"]
    assert translate_helius(tx) == []  # documented gap — see bug_journal BUG-001


def test_swap_native_transfers_currently_funding() -> None:
    # BUG-002: a real AMM swap's incidental SOL transfers become WalletFunded.
    tx = _load("swap_only_native_transfers.json")
    events = translate_helius(tx)
    assert len(events) >= 1
    assert {e.EVENT_TYPE for e in events} == {"WalletFunded"}  # spurious — BUG-002
