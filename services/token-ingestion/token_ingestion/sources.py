"""Pluggable token-discovery sources.

Each source yields normalized :class:`TokenCreated` events. The concrete network
I/O (REST polling / WS / gRPC) is isolated here; real credentials come from
``settings``. Stubs raise no errors when unconfigured — they simply idle — so the
platform boots cleanly before keys are provisioned.
"""

from __future__ import annotations

import abc
import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone

import httpx

from mchpai_common.config import settings
from mchpai_common.events.types import TokenCreated
from mchpai_common.logging import get_logger
from mchpai_common.schemas.common import TokenSource

log = get_logger("token-ingestion.sources")


class Source(abc.ABC):
    name: TokenSource

    @abc.abstractmethod
    async def stream(self) -> AsyncIterator[TokenCreated]:  # pragma: no cover - interface
        if False:
            yield  # make this an async generator
        raise NotImplementedError


class PumpFunSource(Source):
    """New mints from Pump.fun. Real impl subscribes to the pump.fun WS feed."""

    name = TokenSource.pumpfun

    async def stream(self) -> AsyncIterator[TokenCreated]:
        # Placeholder loop: a production build connects to the pump.fun websocket
        # ("subscribeNewToken") and yields each creation. Idles if unconfigured.
        while True:
            await asyncio.sleep(5)
            if False:
                yield  # pragma: no cover


class HeliusSource(Source):
    """New mints via Helius enhanced transactions / webhooks."""

    name = TokenSource.helius

    async def stream(self) -> AsyncIterator[TokenCreated]:
        if not settings.helius_api_key:
            log.warning("helius.no_api_key — source idle")
            while True:
                await asyncio.sleep(30)
                if False:
                    yield  # pragma: no cover
        # Production: poll Helius for InitializeMint events and yield TokenCreated.
        async with httpx.AsyncClient(timeout=10) as _client:  # noqa: F841
            while True:
                await asyncio.sleep(2)
                if False:
                    yield  # pragma: no cover


class YellowstoneSource(Source):
    """New mints from a Yellowstone Geyser gRPC stream (lowest latency)."""

    name = TokenSource.yellowstone

    async def stream(self) -> AsyncIterator[TokenCreated]:
        # The Rust execution-engine owns the latency-critical Yellowstone stream;
        # this Python source is for discovery/backfill and can run independently.
        while True:
            await asyncio.sleep(5)
            if False:
                yield  # pragma: no cover


def build_sources() -> list[Source]:
    """Instantiate all configured discovery sources."""
    return [PumpFunSource(), HeliusSource(), YellowstoneSource()]


def _now() -> datetime:
    return datetime.now(timezone.utc)
