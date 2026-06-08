"""Time and sequence primitives.

A wallet is a *movie, not a snapshot*. Everything in the Wallet Intelligence
System is therefore indexed by time and ordered by an explicit, monotonic
sequence. This module defines the vocabulary the rest of the system uses to
talk about *when* something happened and *in what order* we became aware of it.

Two distinct clocks are tracked for every fact, because conflating them is the
single most common source of look-ahead leakage in quantitative systems:

* ``event_time`` — when the thing happened in the world (e.g. block time of a
  swap). This is what we reason about for behavior.
* ``ingestion_time`` — when *we* learned about it. Point-in-time correctness
  means a feature computed "as of" T may only use facts whose
  ``ingestion_time <= T``. Reality has priority over prediction: we never let
  the system see a fact before it could plausibly have known it.

The ``Sequence`` is a global, gap-free, strictly increasing integer assigned by
the event store at append time. It is the spine of replay determinism: given
the same ordered sequence of events, every projection in the system MUST
produce byte-identical state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import NewType

# A nanosecond-resolution UNIX timestamp. Integers (not floats) so that ordering
# and equality are exact and replay is deterministic across platforms.
Nanos = NewType("Nanos", int)

# Global monotonic position in the event log. Assigned by the store, never by a
# producer. Gap-free and strictly increasing.
Sequence = NewType("Sequence", int)

NANOS_PER_SECOND = 1_000_000_000


def now_nanos() -> Nanos:
    """Wall-clock nanoseconds. Used ONLY at the edge (ingestion), never inside
    projections or feature computation, where it would destroy determinism."""
    return Nanos(int(datetime.now(tz=UTC).timestamp() * NANOS_PER_SECOND))


def to_datetime(ns: Nanos) -> datetime:
    return datetime.fromtimestamp(ns / NANOS_PER_SECOND, tz=UTC)


def from_datetime(dt: datetime) -> Nanos:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return Nanos(int(dt.timestamp() * NANOS_PER_SECOND))


@dataclass(frozen=True, slots=True, order=True)
class TimePoint:
    """An instant ``t`` at which we observe ``wallet_state(t)`` / ``graph(t)``.

    Ordered by ``event_time`` first, then ``ingestion_time`` then ``sequence``,
    so that a list of TimePoints sorts into a deterministic, causally-consistent
    timeline.
    """

    event_time: Nanos
    ingestion_time: Nanos
    sequence: Sequence

    def as_datetime(self) -> datetime:
        return to_datetime(self.event_time)


@dataclass(frozen=True, slots=True)
class Interval:
    """A half-open time window ``[start, end)`` used for windowed features."""

    start: Nanos
    end: Nanos

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(f"Interval end {self.end} precedes start {self.start}")

    def contains(self, ns: Nanos) -> bool:
        return self.start <= ns < self.end

    @property
    def duration_nanos(self) -> int:
        return int(self.end) - int(self.start)


# Common window durations, expressed in nanoseconds, for windowed features.
SECOND = NANOS_PER_SECOND
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR
WEEK = 7 * DAY
