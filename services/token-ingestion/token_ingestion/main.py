"""token-ingestion entrypoint.

Fans every discovery source into the bus as ``TokenCreated`` events and upserts
the token into the Postgres truth DB. Horizontally scalable: shard sources across
replicas via config.
"""

from __future__ import annotations

import asyncio

from mchpai_common.config import settings
from mchpai_common.database import get_pg_pool
from mchpai_common.events import EventBus
from mchpai_common.events.types import EventType, TokenCreated
from mchpai_common.logging import configure as configure_logging, get_logger
from mchpai_common.metrics import TOKENS_DISCOVERED, start_metrics_server

from .sources import Source, build_sources

SERVICE = "token-ingestion"


async def persist_token(pool, ev: TokenCreated) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO tokens (mint, symbol, name, creator, source, created_at)
            VALUES ($1,$2,$3,$4,$5,$6)
            ON CONFLICT (mint) DO UPDATE
              SET symbol = COALESCE(EXCLUDED.symbol, tokens.symbol),
                  name   = COALESCE(EXCLUDED.name, tokens.name),
                  updated_at = now()
            """,
            ev.mint, ev.symbol, ev.name, ev.creator, ev.source.value, ev.created_at,
        )


async def pump_source(bus: EventBus, pool, source: Source, log) -> None:
    log.info("source.start", source=source.name.value)
    async for ev in source.stream():
        await persist_token(pool, ev)
        await bus.publish(EventType.TOKEN_CREATED, ev, partition_key=ev.mint)
        TOKENS_DISCOVERED.labels(source=ev.source.value).inc()
        log.info("token.discovered", mint=ev.mint, source=ev.source.value)


async def main() -> None:
    configure_logging(level=settings.log_level, fmt=settings.log_format, service=SERVICE)
    log = get_logger(SERVICE)
    start_metrics_server(settings.prometheus_port)

    pool = await get_pg_pool()
    bus = await EventBus(settings.nats_url, producer=SERVICE).connect()
    await bus.ensure_streams()

    sources = build_sources()
    log.info("token-ingestion.started", sources=[s.name.value for s in sources])
    await asyncio.gather(*(pump_source(bus, pool, s, log) for s in sources))


if __name__ == "__main__":
    asyncio.run(main())
