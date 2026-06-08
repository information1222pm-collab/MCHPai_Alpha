"""The crown property: reality enters through one door.

The same underlying reality — alpha buys GEM, then sells it — expressed through
Helius, Yellowstone, RPC and CSV must reconstruct the *identical* wallet_state(t).
Sources are interchangeable; only the door differs. Provenance (``venue``) may
legitimately tag origin, but it never changes behavior, so it is set aside when
comparing the events themselves.
"""

from __future__ import annotations

import itertools
from dataclasses import replace
from pathlib import Path

from wis.conformance import wallet_world_digest
from wis.domain.events import WalletBoughtToken, WalletSoldToken
from wis.eventsourcing.replay import ReplayEngine
from wis.eventsourcing.store import InMemoryEventStore
from wis.projections.wallet_projector import WalletProjector
from wis.sources import (
    CSVSource,
    HeliusSource,
    RPCSource,
    YellowstoneSource,
    collect,
    pump,
)

T1, T2 = 1_700_000_000, 1_700_003_600
AT1, AT2 = T1 * 1_000_000_000, T2 * 1_000_000_000


def _counter():
    c = itertools.count(1)
    return lambda: next(c)  # deterministic ingestion stamps


def _helius() -> HeliusSource:
    return HeliusSource(
        [
            {"timestamp": T1, "type": "SWAP", "feePayer": "alpha", "events": {"swap": {
                "nativeInput": {"account": "alpha", "amount": "1000000000"},
                "tokenOutputs": [{"mint": "GEM", "rawTokenAmount": {"tokenAmount": "1000000000", "decimals": 6}}]}}},
            {"timestamp": T2, "type": "SWAP", "feePayer": "alpha", "events": {"swap": {
                "tokenInputs": [{"mint": "GEM", "rawTokenAmount": {"tokenAmount": "1000000000", "decimals": 6}}],
                "nativeOutput": {"account": "alpha", "amount": "3000000000"}}}},
        ],
        now=_counter(),
    )


def _yellowstone() -> YellowstoneSource:
    return YellowstoneSource(
        [
            {"block_time": T1, "kind": "swap", "wallet": "alpha", "side": "buy",
             "token": {"mint": "GEM", "amount": "1000000000", "decimals": 6}, "sol_lamports": "1000000000"},
            {"block_time": T2, "kind": "swap", "wallet": "alpha", "side": "sell",
             "token": {"mint": "GEM", "amount": "1000000000", "decimals": 6}, "sol_lamports": "3000000000"},
        ],
        now=_counter(),
    )


def _rpc() -> RPCSource:
    return RPCSource(
        [
            {"blockTime": T1, "transaction": {"message": {"accountKeys": ["alpha"]}}, "meta": {
                "preBalances": [10_000_000_000], "postBalances": [9_000_000_000], "preTokenBalances": [],
                "postTokenBalances": [{"owner": "alpha", "mint": "GEM", "uiTokenAmount": {"amount": "1000000000", "decimals": 6}}]}},
            {"blockTime": T2, "transaction": {"message": {"accountKeys": ["alpha"]}}, "meta": {
                "preBalances": [9_000_000_000], "postBalances": [12_000_000_000],
                "preTokenBalances": [{"owner": "alpha", "mint": "GEM", "uiTokenAmount": {"amount": "1000000000", "decimals": 6}}],
                "postTokenBalances": [{"owner": "alpha", "mint": "GEM", "uiTokenAmount": {"amount": "0", "decimals": 6}}]}},
        ],
        now=_counter(),
    )


def _csv(tmp_path: Path) -> CSVSource:
    csv = (
        "event,occurred_at,wallet,token,base_raw,base_decimals,quote_raw,quote_decimals\n"
        f"buy,{AT1},alpha,GEM,1000000000,6,1000000000,9\n"
        f"sell,{AT2},alpha,GEM,1000000000,6,3000000000,9\n"
    )
    path = tmp_path / "s.csv"
    path.write_text(csv, encoding="utf-8")
    return CSVSource(path)


def _strip_venue(payload):
    if isinstance(payload, (WalletBoughtToken, WalletSoldToken)):
        return replace(payload, venue=None)
    return payload


def _digest_via(source) -> str:
    store = InMemoryEventStore()
    pump(source, store)
    return wallet_world_digest(ReplayEngine(store, WalletProjector()).run())


def test_all_sources_reconstruct_identical_state(tmp_path: Path) -> None:
    digests = {
        "helius": _digest_via(_helius()),
        "yellowstone": _digest_via(_yellowstone()),
        "rpc": _digest_via(_rpc()),
        "csv": _digest_via(_csv(tmp_path)),
    }
    assert len(set(digests.values())) == 1, digests


def test_all_sources_emit_identical_events_modulo_provenance(tmp_path: Path) -> None:
    streams = {
        "helius": [_strip_venue(e.payload) for e in collect(_helius())],
        "yellowstone": [_strip_venue(e.payload) for e in collect(_yellowstone())],
        "rpc": [_strip_venue(e.payload) for e in collect(_rpc())],
        "csv": [_strip_venue(e.payload) for e in collect(_csv(tmp_path))],
    }
    reference = streams["helius"]
    for name, events in streams.items():
        assert events == reference, f"{name} diverged from helius"
