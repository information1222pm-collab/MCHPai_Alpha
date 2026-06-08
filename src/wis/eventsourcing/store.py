"""The event store — the system's single source of truth.

Every other store (PostgreSQL projections, ClickHouse analytics, Neo4j graph,
Redis hot cache) is a *derived view* that can be rebuilt by replaying this log.
The log itself is append-only and never mutated. That is what makes the whole
platform auditable and reproducible for decades: any state, at any past instant,
can be regenerated from scratch.

This module defines the :class:`EventStore` protocol and an
:class:`InMemoryEventStore` reference implementation used by tests and research.
Production implementations (NATS JetStream + MinIO archive, PostgreSQL log)
live in :mod:`wis.infra` and satisfy the same protocol.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from wis.domain.events import DomainEvent
from wis.domain.time import Nanos, Sequence, now_nanos
from wis.eventsourcing.event import StoredEvent, derive_event_id


@runtime_checkable
class EventStore(Protocol):
    """Append-only, totally-ordered fact log."""

    def append(self, payload: DomainEvent, *, ingestion_time: Nanos | None = None) -> StoredEvent:
        """Append one event, assigning the next global sequence. Returns the
        stored envelope. ``ingestion_time`` defaults to wall-clock now and may
        be supplied explicitly when back-filling historical data."""
        ...

    def read(
        self,
        *,
        after: Sequence | None = None,
        up_to: Sequence | None = None,
    ) -> Iterator[StoredEvent]:
        """Stream events in sequence order. ``after`` is exclusive, ``up_to`` is
        inclusive — the natural shape for incremental projection cursors."""
        ...

    def read_as_of(self, as_of: Nanos) -> Iterator[StoredEvent]:
        """Stream every event we had *ingested* by instant ``as_of``, in
        sequence order. This is the point-in-time read that powers leak-free
        replay and backtesting."""
        ...

    @property
    def head(self) -> Sequence:
        """The highest assigned sequence (0 if empty)."""
        ...


class InMemoryEventStore:
    """Deterministic reference implementation.

    Sequences are assigned strictly monotonically starting at 1. The store is
    intentionally simple: correctness and determinism over throughput. It is the
    oracle that production stores are tested against.
    """

    def __init__(self) -> None:
        self._log: list[StoredEvent] = []

    def append(self, payload: DomainEvent, *, ingestion_time: Nanos | None = None) -> StoredEvent:
        seq = Sequence(len(self._log) + 1)
        stored = StoredEvent(
            sequence=seq,
            ingestion_time=ingestion_time if ingestion_time is not None else now_nanos(),
            event_id=derive_event_id(seq, payload),
            payload=payload,
        )
        self._log.append(stored)
        return stored

    def read(
        self,
        *,
        after: Sequence | None = None,
        up_to: Sequence | None = None,
    ) -> Iterator[StoredEvent]:
        for stored in self._log:
            if after is not None and stored.sequence <= after:
                continue
            if up_to is not None and stored.sequence > up_to:
                break
            yield stored

    def read_as_of(self, as_of: Nanos) -> Iterator[StoredEvent]:
        for stored in self._log:
            if stored.visible_as_of(as_of):
                yield stored

    @property
    def head(self) -> Sequence:
        return Sequence(len(self._log))

    def __len__(self) -> int:
        return len(self._log)
