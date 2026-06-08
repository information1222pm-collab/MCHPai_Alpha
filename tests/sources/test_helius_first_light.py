"""Helius First Light: the full pipeline from raw payloads to wallet_state(t),
and the headline proof — the archived live recording replays bit-identically.

This exercises everything except the socket (verified separately with a mocked
API), so the entire path translate → ingest → capture → archive → replay →
verify is proven in-process."""

from __future__ import annotations

import itertools
from pathlib import Path

from wis.domain.identifiers import WalletAddress
from wis.eventsourcing.replay import ReplayEngine
from wis.projections.wallet_projector import WalletProjector
from wis.sources.archive_source import ArchiveSource
from wis.sources.base import collect
from wis.sources.helius_live import first_light

T1, T2, T3 = 1_700_000_000, 1_700_000_500, 1_700_003_600

# Raw Helius payloads as the transport would yield them (oldest-first).
_PAYLOADS = [
    {  # alpha buys GEM (1 SOL -> 1000 GEM)
        "signature": "s1", "timestamp": T1, "type": "SWAP", "feePayer": "alpha",
        "events": {"swap": {
            "nativeInput": {"account": "alpha", "amount": "1000000000"},
            "tokenOutputs": [{"mint": "GEM", "rawTokenAmount": {"tokenAmount": "1000000000", "decimals": 6}}]}},
    },
    {  # bravo buys GEM (0.5 SOL -> 100 GEM)
        "signature": "s2", "timestamp": T2, "type": "SWAP", "feePayer": "bravo",
        "events": {"swap": {
            "nativeInput": {"account": "bravo", "amount": "500000000"},
            "tokenOutputs": [{"mint": "GEM", "rawTokenAmount": {"tokenAmount": "100000000", "decimals": 6}}]}},
    },
    {  # alpha sells GEM (1000 GEM -> 3 SOL)
        "signature": "s3", "timestamp": T3, "type": "SWAP", "feePayer": "alpha",
        "events": {"swap": {
            "tokenInputs": [{"mint": "GEM", "rawTokenAmount": {"tokenAmount": "1000000000", "decimals": 6}}],
            "nativeOutput": {"account": "alpha", "amount": "3000000000"}}},
    },
]


def _counter():
    c = itertools.count(1)
    return lambda: next(c)


def test_live_recording_is_replayable(tmp_path: Path) -> None:
    result, _store = first_light(_PAYLOADS, tmp_path / "fl.jsonl", now=_counter())
    assert result.events_observed == 3
    assert result.wallets == ("alpha", "bravo")
    # THE PROOF: the archived recording replays to bit-identical state.
    assert result.replayable
    assert result.live_digest == result.replay_digest


def test_wallet_state_reflects_observed_reality(tmp_path: Path) -> None:
    _result, store = first_light(_PAYLOADS, tmp_path / "fl.jsonl", now=_counter())
    world = ReplayEngine(store, WalletProjector()).run()

    alpha = world.wallets[WalletAddress("alpha")]
    frame = alpha.frame(prices=world.prices)
    assert frame.sample_size == 1  # one round trip
    assert frame.performance.lifetime_roi == 2.0  # paid 1 SOL, received 3 SOL

    bravo = world.wallets[WalletAddress("bravo")]
    assert bravo.closed_trade_count == 0  # still holding
    assert len(bravo.open_positions()) == 1


def test_archive_on_disk_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "fl.jsonl"
    result, store = first_light(_PAYLOADS, path, now=_counter())

    # Independently re-read the archive and confirm identical state.
    from wis.conformance import wallet_world_digest

    replay_store_world = ReplayEngine(_loaded(path), WalletProjector()).run()
    assert wallet_world_digest(replay_store_world) == result.live_digest


def test_recording_is_deterministic(tmp_path: Path) -> None:
    a = (tmp_path / "a.jsonl")
    b = (tmp_path / "b.jsonl")
    first_light(_PAYLOADS, a, now=_counter())
    first_light(_PAYLOADS, b, now=_counter())
    # Same payloads + same receipt clock → byte-identical archive recording.
    assert a.read_bytes() == b.read_bytes()


def test_archive_source_yields_observed_events(tmp_path: Path) -> None:
    path = tmp_path / "fl.jsonl"
    first_light(_PAYLOADS, path, now=_counter())
    events = collect(ArchiveSource(path))
    assert len(events) == 3
    assert {e.payload.EVENT_TYPE for e in events} == {"WalletBoughtToken", "WalletSoldToken"}


def _loaded(path: Path):
    from wis.eventsourcing.store import InMemoryEventStore
    from wis.sources.base import pump

    store = InMemoryEventStore()
    pump(ArchiveSource(path), store)
    return store
