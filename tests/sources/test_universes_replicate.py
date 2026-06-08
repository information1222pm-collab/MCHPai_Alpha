"""The replication instrument: discovery parsers (pure) and the measurement
harness. These are tested without a network — the telescope works on sample data,
and produces distributions only when fed real payloads."""

from __future__ import annotations

from wis.research.reality_lab.replicate import measure
from wis.research.reality_lab.universes import (
    UNIVERSES,
    fee_payers_from_block,
    fee_payers_from_enhanced,
)

_TS = 1_700_000_000  # block time (real Helius payloads always carry one)
_BUY = {"type": "SWAP", "timestamp": _TS, "feePayer": "alpha", "events": {"swap": {
    "nativeInput": {"amount": "1000000000"},
    "tokenOutputs": [{"mint": "GEM", "rawTokenAmount": {"tokenAmount": "1000000000", "decimals": 6}}]}}}
_T2T = {"type": "SWAP", "timestamp": _TS, "feePayer": "alpha", "events": {"swap": {
    "nativeInput": None, "nativeOutput": None,
    "tokenInputs": [{"mint": "USDC", "rawTokenAmount": {"tokenAmount": "5", "decimals": 6}}],
    "tokenOutputs": [{"mint": "GEM", "rawTokenAmount": {"tokenAmount": "9", "decimals": 6}}]}}}
_TRANSFER = {"type": "TRANSFER", "timestamp": _TS, "feePayer": "bravo", "nativeTransfers": [
    {"fromUserAccount": "bravo", "toUserAccount": "vault", "amount": 50_000},      # dust
    {"fromUserAccount": "vault", "toUserAccount": "bravo", "amount": 2_039_280}]}   # ata_rent


def test_fee_payers_from_enhanced_dedupes_in_order() -> None:
    txs = [{"feePayer": "a"}, {"feePayer": "b"}, {"feePayer": "a"}, {"feePayer": "c"}]
    assert fee_payers_from_enhanced(txs) == ["a", "b", "c"]


def test_fee_payers_from_block_skips_votes_and_handles_encodings() -> None:
    block = {"transactions": [
        {"transaction": {"message": {"accountKeys": ["Vote111111111111111111111111111111111111111", "x"]}}},
        {"transaction": {"message": {"accountKeys": ["walletX", "prog"]}}},
        {"transaction": {"message": {"accountKeys": [{"pubkey": "walletY"}, {"pubkey": "prog"}]}}},
    ]}
    assert fee_payers_from_block(block) == ["walletX", "walletY"]


def test_measure_computes_bug_distributions() -> None:
    d = measure([_BUY, _T2T, _TRANSFER])
    assert d.n_transactions == 3
    assert d.n_parsed_swaps == 2
    assert d.p_bug_001 == 0.5            # 1 of 2 parsed swaps is token-to-token
    assert d.p_swap_untranslated == 0.5  # only the buy yields a trade
    assert d.n_native_transfers == 2
    assert d.p_bug_002_mechanics == 1.0  # dust + ata_rent are both mechanics
    assert d.trade_events == 1 and d.funding_events == 2
    assert d.funding_trade_ratio == 2.0


def test_registry_is_honest_about_status() -> None:
    slugs = [u.slug for u in UNIVERSES]
    assert len(slugs) == len(set(slugs)) == 8
    observed = [u for u in UNIVERSES if u.status == "observed"]
    # Only the universe we actually have an archive for is marked observed.
    assert [u.slug for u in observed] == ["active_traders"]
    # Every universe documents at least one bias — naming distortion is the science.
    assert all(u.biases for u in UNIVERSES)
