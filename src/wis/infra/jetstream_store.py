"""An EventStore on NATS JetStream — the durable event backbone.

JetStream gives us exactly what the log needs: a durable, ordered, gap-free
per-stream sequence. We publish one message per event and adopt JetStream's
stream sequence as our :class:`~wis.domain.time.Sequence`, so ordering is owned
by the broker and shared by every consumer. ``event_id`` is *recomputed* on read
via ``derive_event_id(sequence, payload)`` rather than stored — it is a pure
function of the two, so it always matches the oracle.

Async ``nats-py`` is wrapped behind the synchronous EventStore protocol with a
private event loop, so this adapter drops into the same conformance harness as
every other store. Correctness first; a fully-async path can come later behind
the same verified contract.

The driver is imported lazily so the module is importable without the extra.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

from wis.domain.events import DomainEvent
from wis.domain.time import Nanos, Sequence, now_nanos
from wis.eventsourcing.codec import dumps_payload, loads_payload
from wis.eventsourcing.event import StoredEvent, derive_event_id

_INGESTION_HEADER = "Wis-Ingestion-Time"


class JetStreamEventStore:
    """Satisfies :class:`~wis.eventsourcing.store.EventStore`."""

    def __init__(self, url: str, *, stream: str = "wis-events", subject: str | None = None) -> None:
        self._url = url
        self._stream = stream
        self._subject = subject or f"{stream}.events"
        self._loop = asyncio.new_event_loop()
        self._nc = None
        self._js = None
        self._run(self._connect())

    # -- public sync API ---------------------------------------------------

    def append(self, payload: DomainEvent, *, ingestion_time: Nanos | None = None) -> StoredEvent:
        ingestion = ingestion_time if ingestion_time is not None else now_nanos()
        seq = self._run(self._publish(payload, ingestion))
        return StoredEvent(
            sequence=seq,
            ingestion_time=ingestion,
            event_id=derive_event_id(seq, payload),
            payload=payload,
        )

    def read(
        self, *, after: Sequence | None = None, up_to: Sequence | None = None
    ) -> Iterator[StoredEvent]:
        lo = int(after) + 1 if after is not None else 1
        hi = int(up_to) if up_to is not None else int(self.head)
        for s in range(lo, hi + 1):
            stored = self._run(self._get(s))
            if stored is not None:
                yield stored

    def read_as_of(self, as_of: Nanos) -> Iterator[StoredEvent]:
        for stored in self.read():
            if stored.visible_as_of(as_of):
                yield stored

    @property
    def head(self) -> Sequence:
        return Sequence(self._run(self._last_seq()))

    def close(self) -> None:
        self._run(self._nc.drain()) if self._nc else None
        self._loop.close()

    # -- async internals ---------------------------------------------------

    def _run(self, coro):
        return self._loop.run_until_complete(coro)

    async def _connect(self) -> None:
        import nats  # lazy

        self._nc = await nats.connect(self._url)
        self._js = self._nc.jetstream()
        try:
            await self._js.stream_info(self._stream)
        except Exception:
            await self._js.add_stream(name=self._stream, subjects=[self._subject])

    async def _publish(self, payload: DomainEvent, ingestion: Nanos) -> Sequence:
        ack = await self._js.publish(
            self._subject,
            dumps_payload(payload).encode(),
            headers={_INGESTION_HEADER: str(int(ingestion))},
        )
        return Sequence(int(ack.seq))

    async def _get(self, seq: int) -> StoredEvent | None:
        try:
            msg = await self._js.get_msg(self._stream, seq)
        except Exception:
            return None
        ingestion = Nanos(int(msg.headers[_INGESTION_HEADER]))
        payload = loads_payload(msg.data.decode())
        return StoredEvent(
            sequence=Sequence(seq),
            ingestion_time=ingestion,
            event_id=derive_event_id(Sequence(seq), payload),
            payload=payload,
        )

    async def _last_seq(self) -> int:
        info = await self._js.stream_info(self._stream)
        return int(info.state.last_seq)
