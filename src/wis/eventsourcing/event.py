"""The persisted event envelope.

A :class:`DomainEvent` is what *happened*; a :class:`StoredEvent` is that fact
as it lives in the immutable log, wrapped with the metadata the store is
responsible for: a global gap-free ``sequence``, the ``ingestion_time`` at
which we learned of it, and a stable ``event_id``. The envelope is what
guarantees ordering and point-in-time correctness; the payload never carries
this metadata so producers cannot forge it.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from wis.domain.events import DomainEvent
from wis.domain.time import Nanos, Sequence, TimePoint


@dataclass(frozen=True, slots=True)
class StoredEvent:
    sequence: Sequence
    ingestion_time: Nanos
    event_id: str
    payload: DomainEvent

    @property
    def event_time(self) -> Nanos:
        return self.payload.occurred_at

    @property
    def event_type(self) -> str:
        return self.payload.EVENT_TYPE

    @property
    def time_point(self) -> TimePoint:
        return TimePoint(
            event_time=self.event_time,
            ingestion_time=self.ingestion_time,
            sequence=self.sequence,
        )

    def visible_as_of(self, as_of: Nanos) -> bool:
        """Point-in-time gate: this fact is only knowable at or after the
        instant we ingested it. The single rule that keeps features leak-free."""
        return self.ingestion_time <= as_of


def derive_event_id(sequence: Sequence, payload: DomainEvent) -> str:
    """Deterministic content-addressed id. Same sequence + same payload always
    yields the same id, which makes replays and de-duplication idempotent."""
    h = hashlib.sha256()
    h.update(str(sequence).encode())
    h.update(payload.EVENT_TYPE.encode())
    h.update(repr(payload).encode())
    return h.hexdigest()[:32]
