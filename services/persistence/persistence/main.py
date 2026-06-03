"""persistence entrypoint."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from mchpai_common.config import settings
from mchpai_common.database import get_clickhouse, get_pg_pool, get_redis
from mchpai_common.events import Envelope, EventBus
from mchpai_common.events.subjects import STREAMS, PREFIX, TOKEN_CREATED
from mchpai_common.events.types import EventType
from mchpai_common.logging import configure as configure_logging, get_logger
from mchpai_common.metrics import EVENTS_CONSUMED, start_metrics_server

SERVICE = "persistence"
EVENT_LOG_COLUMNS = ["occurred_at", "event_type", "event_id", "producer", "partition_key", "payload"]


async def record_birth(pool, p: dict) -> bool:
    """Idempotently record a token birth. Returns True if it was a new birth."""
    ts = p.get("created_at")
    when = datetime.fromisoformat(ts) if ts else datetime.now(timezone.utc)
    async with pool.acquire() as conn:
        # token_births is immutable: ON CONFLICT DO NOTHING — never overwrite.
        res = await conn.execute(
            """
            INSERT INTO token_births
              (mint, birth_slot, birth_timestamp, creator, launchpad,
               initial_liquidity_sol, initial_market_cap_sol)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
            ON CONFLICT (mint) DO NOTHING
            """,
            p["mint"], p.get("first_seen_slot"), when, p.get("creator"),
            p.get("source", "unknown"), p.get("initial_liquidity_sol"), None,
        )
        await conn.execute(
            "INSERT INTO tokens (mint, symbol, name, creator, source, created_at) "
            "VALUES ($1,$2,$3,$4,$5,$6) ON CONFLICT (mint) DO NOTHING",
            p["mint"], p.get("symbol"), p.get("name"), p.get("creator"),
            p.get("source", "unknown"), when,
        )
    return res.endswith("1")


async def main() -> None:
    configure_logging(level=settings.log_level, fmt=settings.log_format, service=SERVICE)
    log = get_logger(SERVICE)
    start_metrics_server(settings.prometheus_port)

    pool = await get_pg_pool()
    rds = get_redis()
    ch = get_clickhouse()
    bus = await EventBus(settings.nats_url, producer=SERVICE).connect()
    await bus.ensure_streams()

    async def archive(env: Envelope) -> None:
        EVENTS_CONSUMED.labels(event_type=env.type, service=SERVICE).inc()
        # 1) immutable event log
        try:
            ch.insert(
                "event_log",
                [[env.occurred_at, env.type, env.id, env.producer,
                  env.partition_key or "", __import__("orjson").dumps(env.payload).decode()]],
                column_names=EVENT_LOG_COLUMNS,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("event_log.insert_failed", error=str(exc))

        # 2) progress counters (the march to 1,000,000)
        await rds.incr("stats:events")
        await rds.incr(f"stats:events:{env.type}")
        if env.type == EventType.TOKEN_SNAPSHOT.value:
            await rds.incr("stats:snapshots")

        # 3) sacred births
        if env.type == EventType.TOKEN_CREATED.value:
            is_new = await record_birth(pool, env.payload)
            if is_new:
                await rds.incr("stats:births")
                await rds.incr("stats:tokens")
                log.info("birth.recorded", mint=env.payload.get("mint"))

    # subscribe to every domain stream (full firehose)
    for name, subject in STREAMS.items():
        await bus.subscribe(subject, archive, durable=f"{SERVICE}.{name.lower()}")
    log.info("persistence.started", streams=list(STREAMS))
    await bus.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
