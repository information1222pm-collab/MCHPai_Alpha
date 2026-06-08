"""ArchiveSource is the deterministic laboratory: capture a log, replay it, and
reconstruct bit-identical wallet_state(t) — every time, including from Parquet."""

from __future__ import annotations

from pathlib import Path

import pytest

from wis.conformance import canonical_event_log, wallet_world_digest
from wis.eventsourcing.replay import ReplayEngine
from wis.eventsourcing.store import InMemoryEventStore
from wis.projections.wallet_projector import WalletProjector
from wis.sources import ArchiveSource, capture, pump, write_jsonl


def _oracle() -> InMemoryEventStore:
    store = InMemoryEventStore()
    for payload, ingestion in canonical_event_log():
        store.append(payload, ingestion_time=ingestion)
    return store


def _digest(store: InMemoryEventStore) -> str:
    return wallet_world_digest(ReplayEngine(store, WalletProjector()).run())


def test_archive_roundtrip_reproduces_state(tmp_path: Path) -> None:
    oracle = _oracle()
    path = tmp_path / "log.jsonl"
    write_jsonl(capture(oracle), path)

    replayed = InMemoryEventStore()
    pump(ArchiveSource(path), replayed)

    assert _digest(replayed) == _digest(oracle)


def test_archive_replay_is_deterministic(tmp_path: Path) -> None:
    oracle = _oracle()
    path = tmp_path / "log.jsonl"
    write_jsonl(capture(oracle), path)

    a, b = InMemoryEventStore(), InMemoryEventStore()
    pump(ArchiveSource(path), a)
    pump(ArchiveSource(path), b)
    assert _digest(a) == _digest(b)


def test_archive_preserves_ingestion_time(tmp_path: Path) -> None:
    oracle = _oracle()
    path = tmp_path / "log.jsonl"
    write_jsonl(capture(oracle), path)

    replayed = InMemoryEventStore()
    pump(ArchiveSource(path), replayed)
    # Point-in-time visibility must survive the round trip, event for event.
    assert [int(e.ingestion_time) for e in replayed.read()] == [
        int(e.ingestion_time) for e in oracle.read()
    ]


def test_archive_parquet_roundtrip(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    from wis.sources.archive_source import write_parquet

    oracle = _oracle()
    path = tmp_path / "log.parquet"
    write_parquet(capture(oracle), path)

    replayed = InMemoryEventStore()
    pump(ArchiveSource(path), replayed)
    assert _digest(replayed) == _digest(oracle)
