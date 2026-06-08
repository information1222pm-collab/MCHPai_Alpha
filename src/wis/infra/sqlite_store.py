"""A durable, file-backed EventStore on SQLite.

SQLite needs no server, ships with Python, and is a *real* database writing to a
*real* file — which makes it the perfect in-process proof that the persistence
abstraction is sound: it passes the exact same oracle-conformance harness as the
production adapters, and a log written to disk replays to bit-identical state
after the process restarts. It is both a genuinely useful embedded store and the
template every server-backed adapter follows.

Correctness over speed, always: sequences are assigned under a transaction so
the log is gap-free and append order is total. Event ids match the in-memory
oracle's (``derive_event_id(sequence, payload)``) so conformance holds field for
field.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

from wis.domain.events import DomainEvent
from wis.domain.time import Nanos, Sequence, now_nanos
from wis.eventsourcing.codec import dumps_payload, loads_payload
from wis.eventsourcing.event import StoredEvent, derive_event_id

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    sequence       INTEGER PRIMARY KEY,
    ingestion_time INTEGER NOT NULL,
    event_id       TEXT    NOT NULL,
    event_type     TEXT    NOT NULL,
    event_version  INTEGER NOT NULL,
    payload        TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS events_ingestion ON events (ingestion_time, sequence);
"""


class SqliteEventStore:
    """Satisfies :class:`~wis.eventsourcing.store.EventStore`."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)

    def append(self, payload: DomainEvent, *, ingestion_time: Nanos | None = None) -> StoredEvent:
        ingestion = ingestion_time if ingestion_time is not None else now_nanos()
        # Assign the next sequence atomically: BEGIN IMMEDIATE takes the write
        # lock so concurrent appends cannot collide on the sequence.
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            row = self._conn.execute("SELECT COALESCE(MAX(sequence), 0) FROM events").fetchone()
            seq = Sequence(int(row[0]) + 1)
            event_id = derive_event_id(seq, payload)
            self._conn.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)",
                (
                    int(seq),
                    int(ingestion),
                    event_id,
                    payload.EVENT_TYPE,
                    payload.event_version,
                    dumps_payload(payload),
                ),
            )
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise
        return StoredEvent(sequence=seq, ingestion_time=ingestion, event_id=event_id, payload=payload)

    def read(
        self, *, after: Sequence | None = None, up_to: Sequence | None = None
    ) -> Iterator[StoredEvent]:
        clauses, params = [], []
        if after is not None:
            clauses.append("sequence > ?")
            params.append(int(after))
        if up_to is not None:
            clauses.append("sequence <= ?")
            params.append(int(up_to))
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT sequence, ingestion_time, event_id, payload FROM events{where} ORDER BY sequence"
        yield from self._rows(sql, params)

    def read_as_of(self, as_of: Nanos) -> Iterator[StoredEvent]:
        sql = (
            "SELECT sequence, ingestion_time, event_id, payload FROM events "
            "WHERE ingestion_time <= ? ORDER BY sequence"
        )
        yield from self._rows(sql, [int(as_of)])

    @property
    def head(self) -> Sequence:
        row = self._conn.execute("SELECT COALESCE(MAX(sequence), 0) FROM events").fetchone()
        return Sequence(int(row[0]))

    def close(self) -> None:
        self._conn.close()

    def _rows(self, sql: str, params: list) -> Iterator[StoredEvent]:
        for seq, ingestion, event_id, payload in self._conn.execute(sql, params):
            yield StoredEvent(
                sequence=Sequence(int(seq)),
                ingestion_time=Nanos(int(ingestion)),
                event_id=event_id,
                payload=loads_payload(payload),
            )
