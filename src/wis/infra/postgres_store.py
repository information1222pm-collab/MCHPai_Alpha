"""A durable EventStore on PostgreSQL — the system of record.

PostgreSQL holds the canonical, append-only fact log. It satisfies the same
:class:`~wis.eventsourcing.store.EventStore` protocol as the in-memory oracle
and is held to the same bar by ``assert_eventstore_conforms``: identical
sequencing, identical point-in-time visibility, bit-identical replay.

Sequence assignment is gap-free and total-ordered: each append takes a
transaction-scoped advisory lock before reading ``MAX(sequence)+1``, so
concurrent writers can never collide or leave a hole. Correctness over speed —
when throughput demands it, batching and a Rust hot path can come later, behind
this same verified contract.

The psycopg driver is imported lazily so this module can be inspected without
the ``infra`` extra installed.
"""

from __future__ import annotations

from collections.abc import Iterator

from wis.domain.events import DomainEvent
from wis.domain.time import Nanos, Sequence, now_nanos
from wis.eventsourcing.codec import decode_payload, dumps_payload
from wis.eventsourcing.event import StoredEvent, derive_event_id

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    sequence       BIGINT PRIMARY KEY,
    ingestion_time BIGINT NOT NULL,
    event_id       TEXT   NOT NULL,
    event_type     TEXT   NOT NULL,
    event_version  INTEGER NOT NULL,
    payload        JSONB  NOT NULL
);
CREATE INDEX IF NOT EXISTS events_ingestion ON events (ingestion_time, sequence);
"""

# Arbitrary fixed key for the append advisory lock — all writers serialize here.
_APPEND_LOCK_KEY = 0x5749_5345  # "WISE"


class PostgresEventStore:
    """Satisfies :class:`~wis.eventsourcing.store.EventStore`."""

    def __init__(self, dsn: str) -> None:
        import psycopg  # lazy

        self._conn = psycopg.connect(dsn, autocommit=False)
        with self._conn.cursor() as cur:
            cur.execute(_SCHEMA)
        self._conn.commit()

    def append(self, payload: DomainEvent, *, ingestion_time: Nanos | None = None) -> StoredEvent:
        ingestion = ingestion_time if ingestion_time is not None else now_nanos()
        try:
            with self._conn.cursor() as cur:
                # Serialize sequence assignment across all writers.
                cur.execute("SELECT pg_advisory_xact_lock(%s)", (_APPEND_LOCK_KEY,))
                cur.execute("SELECT COALESCE(MAX(sequence), 0) FROM events")
                seq = Sequence(int(cur.fetchone()[0]) + 1)
                event_id = derive_event_id(seq, payload)
                cur.execute(
                    "INSERT INTO events VALUES (%s, %s, %s, %s, %s, %s)",
                    (
                        int(seq),
                        int(ingestion),
                        event_id,
                        payload.EVENT_TYPE,
                        payload.event_version,
                        dumps_payload(payload),
                    ),
                )
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        return StoredEvent(sequence=seq, ingestion_time=ingestion, event_id=event_id, payload=payload)

    def read(
        self, *, after: Sequence | None = None, up_to: Sequence | None = None
    ) -> Iterator[StoredEvent]:
        clauses, params = [], []
        if after is not None:
            clauses.append("sequence > %s")
            params.append(int(after))
        if up_to is not None:
            clauses.append("sequence <= %s")
            params.append(int(up_to))
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT sequence, ingestion_time, event_id, payload FROM events{where} ORDER BY sequence"
        yield from self._rows(sql, params)

    def read_as_of(self, as_of: Nanos) -> Iterator[StoredEvent]:
        sql = (
            "SELECT sequence, ingestion_time, event_id, payload FROM events "
            "WHERE ingestion_time <= %s ORDER BY sequence"
        )
        yield from self._rows(sql, [int(as_of)])

    @property
    def head(self) -> Sequence:
        with self._conn.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(sequence), 0) FROM events")
            return Sequence(int(cur.fetchone()[0]))

    def close(self) -> None:
        self._conn.close()

    def _rows(self, sql: str, params: list) -> Iterator[StoredEvent]:
        import json

        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            for seq, ingestion, event_id, payload in cur.fetchall():
                # JSONB decodes to a dict (key order is irrelevant to the codec);
                # a string column would arrive as text. Handle both.
                data = payload if isinstance(payload, dict) else json.loads(payload)
                yield StoredEvent(
                    sequence=Sequence(int(seq)),
                    ingestion_time=Nanos(int(ingestion)),
                    event_id=event_id,
                    payload=decode_payload(data),
                )
