"""Standard service runtime.

Every Python microservice is a thin ``main`` that builds a :class:`Service`,
registers event handlers, and calls ``run()``. This wires logging, metrics, the
health/metrics HTTP server, and the EventBus identically everywhere, so all 100+
future services share the same operational shape.
"""

from __future__ import annotations

import asyncio
import signal
from collections.abc import Awaitable, Callable

from .config import settings
from .events import EventBus, Envelope
from .logging import configure as configure_logging, get_logger
from .metrics import start_metrics_server


class Service:
    def __init__(self, name: str) -> None:
        self.name = name
        configure_logging(level=settings.log_level, fmt=settings.log_format, service=name)
        self.log = get_logger(name)
        self.bus = EventBus(settings.nats_url, producer=name)
        self._stop = asyncio.Event()
        self._subscriptions: list[tuple[str, Callable[[Envelope], Awaitable[None]], str]] = []

    def on(self, subject: str, durable: str | None = None):
        """Decorator to register a handler for a subject."""

        def deco(fn: Callable[[Envelope], Awaitable[None]]):
            self._subscriptions.append((subject, fn, durable or f"{self.name}.{subject}"))
            return fn

        return deco

    async def run(self, *, metrics: bool = True) -> None:
        if metrics:
            start_metrics_server(settings.prometheus_port)
        await self.bus.connect()
        await self.bus.ensure_streams()
        for subject, handler, durable in self._subscriptions:
            await self.bus.subscribe(subject, handler, durable=durable)

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self._stop.set)
            except NotImplementedError:
                pass

        self.log.info("service.started", name=self.name, env=settings.mchpai_env)
        await self._stop.wait()
        await self.bus.close()
        self.log.info("service.stopped", name=self.name)
