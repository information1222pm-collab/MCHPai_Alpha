"""The Source abstraction — reality enters through one door.

A :class:`Source` is anything that turns observations of the world into the
system's **domain events**. Every source — a historical archive, a Helius
webhook, a Yellowstone gRPC stream, a plain RPC poll, a CSV, a synthetic chaos
generator — emits the *same* domain events. They are therefore interchangeable:
swap the source, and nothing downstream changes.

The pipeline is, always::

    Source → Domain Events → Event Log → Replay → wallet_state(t)

A source never builds wallet state directly. It only feeds the log. The log
remains the single source of truth, and replay over the log remains
deterministic. This is what makes a live Helius feed and a year-old archive
fungible inputs to the exact same intelligence.

Each emitted item is a :class:`SourcedEvent`: the event payload plus the
``ingestion_time`` at which we learned of it. Carrying ingestion time here (not
inventing it at append) is what lets an archive *faithfully* reproduce the
original point-in-time visibility — sacred for leak-free replay.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from wis.domain.events import DomainEvent
from wis.domain.time import Nanos
from wis.eventsourcing.store import EventStore


@dataclass(frozen=True, slots=True)
class SourcedEvent:
    """A domain event together with the instant we observed it."""

    payload: DomainEvent
    ingestion_time: Nanos


@runtime_checkable
class Source(Protocol):
    """Emits domain events from some view of reality."""

    name: str

    def event_stream(self) -> Iterator[SourcedEvent]:
        """Yield observed events in observation order. Pure with respect to the
        underlying data: replaying the same source yields the same events."""
        ...


def pump(source: Source, store: EventStore, *, limit: int | None = None) -> int:
    """Drive a source into the event log. The single connector from any source to
    the single source of truth. Returns the number of events appended."""
    n = 0
    for sourced in source.event_stream():
        store.append(sourced.payload, ingestion_time=sourced.ingestion_time)
        n += 1
        if limit is not None and n >= limit:
            break
    return n


def collect(source: Source, *, limit: int | None = None) -> list[SourcedEvent]:
    """Materialize a source's stream — handy for tests and cross-source equality
    checks (the proof that two sources emit identical events)."""
    out: list[SourcedEvent] = []
    for sourced in source.event_stream():
        out.append(sourced)
        if limit is not None and len(out) >= limit:
            break
    return out
