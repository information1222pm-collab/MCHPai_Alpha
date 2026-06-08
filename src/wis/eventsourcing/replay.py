"""Deterministic replay.

A :class:`Projection` is a *pure fold* over the event log: ``(state, event) ->
state`` with no clocks, no randomness, no I/O. The :class:`ReplayEngine` drives
a projection across an :class:`EventStore` and is the beating heart of the
system's reproducibility guarantee:

    Given the same ordered log, replaying a projection ALWAYS yields identical
    state. Bit-for-bit. Today, and in ten years.

Because folds are pure and the engine can stop at any sequence or any
``as_of`` instant, we can reconstruct ``wallet_state(t)`` or ``graph(t)`` for
*any* point in history — the system is a time machine, not a dashboard.
"""

from __future__ import annotations

from typing import Generic, Protocol, TypeVar

from wis.domain.time import Nanos, Sequence
from wis.eventsourcing.event import StoredEvent
from wis.eventsourcing.store import EventStore

S = TypeVar("S")


class Projection(Protocol[S]):
    """A pure, replay-deterministic fold producing a derived view of type ``S``."""

    def initial(self) -> S:
        """The empty state, before any event."""
        ...

    def apply(self, state: S, event: StoredEvent) -> S:
        """Fold one event into the state and return the next state. MUST be a
        pure function of ``(state, event)`` — no wall clock, no RNG, no I/O."""
        ...


T = TypeVar("T")


class ReplayEngine(Generic[T]):
    def __init__(self, store: EventStore, projection: Projection[T]) -> None:
        self._store = store
        self._projection = projection

    def run(
        self,
        *,
        up_to: Sequence | None = None,
        as_of: Nanos | None = None,
    ) -> T:
        """Replay from the beginning to a stopping point and return the state.

        At most one of ``up_to`` (stop at a sequence, inclusive) or ``as_of``
        (only events ingested by this instant — point-in-time correct) may be
        given. With neither, replays the full log.
        """
        if up_to is not None and as_of is not None:
            raise ValueError("Specify at most one of up_to / as_of")

        state = self._projection.initial()
        if as_of is not None:
            events = self._store.read_as_of(as_of)
        else:
            events = self._store.read(up_to=up_to)
        for event in events:
            state = self._projection.apply(state, event)
        return state

    def trace(self, *, up_to: Sequence | None = None):
        """Yield ``(event, state_after)`` for every step. Lets research labs
        watch a projection *evolve* — the movie, frame by frame."""
        state = self._projection.initial()
        for event in self._store.read(up_to=up_to):
            state = self._projection.apply(state, event)
            yield event, state
