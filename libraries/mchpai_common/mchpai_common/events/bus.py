"""EventBus — async publish/subscribe over NATS JetStream.

A deliberately small surface: ``connect``, ``publish``, ``subscribe``,
``ensure_streams``. Durable consumers + queue groups give at-least-once delivery
and horizontal scaling (N replicas of a service share one durable consumer and
load-balance messages). Business code never imports ``nats`` directly.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import nats
import orjson
from nats.js import JetStreamContext
from nats.js.api import RetentionPolicy, StreamConfig

from ..logging import get_logger
from .envelope import Envelope
from .types import EventType, SUBJECT_BY_TYPE
from . import subjects as S

log = get_logger("eventbus")

Handler = Callable[[Envelope], Awaitable[None]]


class EventBus:
    def __init__(self, url: str, *, producer: str = "unknown") -> None:
        self._url = url
        self._producer = producer
        self._nc: nats.NATS | None = None
        self._js: JetStreamContext | None = None

    async def connect(self) -> "EventBus":
        self._nc = await nats.connect(
            self._url,
            name=self._producer,
            max_reconnect_attempts=-1,
            reconnect_time_wait=1,
        )
        self._js = self._nc.jetstream()
        log.info("eventbus.connected", url=self._url, producer=self._producer)
        return self

    async def close(self) -> None:
        if self._nc:
            await self._nc.drain()

    async def ensure_streams(self) -> None:
        """Create the durable JetStream streams (idempotent)."""
        assert self._js is not None
        for name, subj in S.STREAMS.items():
            cfg = StreamConfig(
                name=f"{S.PREFIX}_{name}",
                subjects=[subj],
                retention=RetentionPolicy.LIMITS,
                max_age=7 * 24 * 3600,          # 7 days of replayable history
                max_bytes=20 * 1024**3,
            )
            try:
                await self._js.add_stream(cfg)
            except Exception:  # already exists → update
                await self._js.update_stream(cfg)
            log.info("eventbus.stream_ready", stream=cfg.name, subject=subj)

    async def publish(
        self,
        event_type: EventType,
        payload,
        *,
        trace_id: str | None = None,
        partition_key: str | None = None,
    ) -> None:
        assert self._js is not None
        subject = SUBJECT_BY_TYPE[event_type]
        env = Envelope.wrap(
            event_type.value,
            payload,
            producer=self._producer,
            trace_id=trace_id,
            partition_key=partition_key,
        )
        await self._js.publish(subject, orjson.dumps(env.model_dump(mode="json")))

    async def subscribe(
        self,
        subject: str,
        handler: Handler,
        *,
        durable: str,
        queue: str | None = None,
        manual_ack: bool = True,
    ) -> None:
        """Subscribe with a durable, load-balanced consumer.

        ``durable`` identifies the logical consumer; replicas sharing it form a
        queue group and split the work. The handler receives a typed Envelope.
        """
        assert self._js is not None

        async def _cb(msg) -> None:
            try:
                env = Envelope(**orjson.loads(msg.data))
                await handler(env)
                if manual_ack:
                    await msg.ack()
            except Exception as exc:  # noqa: BLE001
                log.error("eventbus.handler_error", subject=subject, error=str(exc))
                if manual_ack:
                    await msg.nak(delay=2)

        await self._js.subscribe(
            subject,
            durable=durable,
            queue=queue or durable,
            cb=_cb,
            manual_ack=manual_ack,
        )
        log.info("eventbus.subscribed", subject=subject, durable=durable)

    async def run_forever(self) -> None:
        while True:
            await asyncio.sleep(3600)
