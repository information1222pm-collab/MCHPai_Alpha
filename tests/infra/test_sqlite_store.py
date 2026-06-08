"""The SQLite adapter must be indistinguishable from the in-memory oracle, and
a log written to disk must replay to identical state after a restart. This is
the concrete proof that "same log → bit-identical state" survives real
persistence."""

from __future__ import annotations

from pathlib import Path

from wis.conformance import (
    assert_eventstore_conforms,
    canonical_event_log,
    wallet_world_digest,
)
from wis.eventsourcing.replay import ReplayEngine
from wis.eventsourcing.store import InMemoryEventStore
from wis.infra.sqlite_store import SqliteEventStore
from wis.projections.wallet_projector import WalletProjector


def test_sqlite_conforms_to_oracle_in_memory() -> None:
    assert_eventstore_conforms(SqliteEventStore, canonical_event_log())


def test_sqlite_survives_restart_with_identical_replay(tmp_path: Path) -> None:
    db = tmp_path / "events.db"

    # Write the log through one connection, then drop it entirely.
    writer = SqliteEventStore(db)
    for payload, ingestion in canonical_event_log():
        writer.append(payload, ingestion_time=ingestion)
    expected_head = int(writer.head)
    writer.close()

    # Reopen from disk in a fresh store — simulating a process restart.
    reopened = SqliteEventStore(db)
    assert int(reopened.head) == expected_head

    # The replayed state from disk matches the oracle's in-memory replay exactly.
    oracle = InMemoryEventStore()
    for payload, ingestion in canonical_event_log():
        oracle.append(payload, ingestion_time=ingestion)

    disk_world = ReplayEngine(reopened, WalletProjector()).run()
    mem_world = ReplayEngine(oracle, WalletProjector()).run()
    assert wallet_world_digest(disk_world) == wallet_world_digest(mem_world)
    reopened.close()


def test_sqlite_event_ids_match_oracle(tmp_path: Path) -> None:
    store = SqliteEventStore(tmp_path / "ids.db")
    oracle = InMemoryEventStore()
    for payload, ingestion in canonical_event_log():
        store.append(payload, ingestion_time=ingestion)
        oracle.append(payload, ingestion_time=ingestion)
    assert [e.event_id for e in store.read()] == [e.event_id for e in oracle.read()]
