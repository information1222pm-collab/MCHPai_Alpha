"""wallet-ingestion entrypoint.

Bridges the Rust engine's ``raw.swaps`` Redis stream into typed wallet events on
NATS, persists trades to Postgres + ClickHouse, and updates Redis hot state. This
is the seam between the low-latency (Rust/Redis) and analytical (Python/NATS)
planes.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import orjson

from mchpai_common.config import settings
from mchpai_common.database import get_pg_pool, get_redis
from mchpai_common.events import EventBus
from mchpai_common.events.types import EventType, WalletBoughtToken, WalletSoldToken
from mchpai_common.logging import configure as configure_logging, get_logger
from mchpai_common.metrics import EVENTS_PUBLISHED, start_metrics_server
from mchpai_common.schemas.common import Side

SERVICE = "wallet-ingestion"
RAW_SWAPS_STREAM = "raw.swaps"          # produced by the Rust engine
GROUP = "wallet-ingestion"


async def persist_trade(pool, swap: dict) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO trades
              (signature, wallet, mint, side, sol_amount, token_amount, price_sol, program, slot, block_time)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            ON CONFLICT (signature, wallet, mint, side) DO NOTHING
            """,
            swap["signature"], swap["wallet"], swap["mint"], swap["side"],
            float(swap["sol_amount"]), float(swap["token_amount"]),
            swap.get("price_sol"), swap.get("program"), swap.get("slot"),
            datetime.fromtimestamp(swap.get("ts", 0), tz=timezone.utc),
        )


async def update_hot_state(rds, swap: dict) -> None:
    key = f"wallet:hot:{swap['wallet']}"
    # Keep a short rolling list of recent activity for fast feature lookups.
    await rds.lpush(key, orjson.dumps(swap).decode())
    await rds.ltrim(key, 0, 199)
    await rds.expire(key, 7 * 24 * 3600)


async def main() -> None:
    configure_logging(level=settings.log_level, fmt=settings.log_format, service=SERVICE)
    log = get_logger(SERVICE)
    start_metrics_server(settings.prometheus_port)

    pool = await get_pg_pool()
    rds = get_redis()
    bus = await EventBus(settings.nats_url, producer=SERVICE).connect()
    await bus.ensure_streams()

    # Ensure a Redis consumer group on the Rust engine's stream.
    try:
        await rds.xgroup_create(RAW_SWAPS_STREAM, GROUP, id="0", mkstream=True)
    except Exception:
        pass  # group already exists

    log.info("wallet-ingestion.started", stream=RAW_SWAPS_STREAM)
    while True:
        resp = await rds.xreadgroup(GROUP, SERVICE, {RAW_SWAPS_STREAM: ">"}, count=256, block=2000)
        if not resp:
            continue
        for _stream, messages in resp:
            for msg_id, fields in messages:
                swap = orjson.loads(fields["data"]) if "data" in fields else fields
                await persist_trade(pool, swap)
                await update_hot_state(rds, swap)

                side = Side(swap["side"])
                common = dict(
                    wallet=swap["wallet"], mint=swap["mint"], signature=swap["signature"],
                    sol_amount=float(swap["sol_amount"]), token_amount=float(swap["token_amount"]),
                    price_sol=swap.get("price_sol"), slot=swap.get("slot"), program=swap.get("program"),
                )
                if side == Side.buy:
                    await bus.publish(EventType.WALLET_BOUGHT_TOKEN, WalletBoughtToken(**common),
                                      partition_key=swap["wallet"])
                    EVENTS_PUBLISHED.labels(event_type="WalletBoughtToken", service=SERVICE).inc()
                else:
                    await bus.publish(EventType.WALLET_SOLD_TOKEN, WalletSoldToken(**common),
                                      partition_key=swap["wallet"])
                    EVENTS_PUBLISHED.labels(event_type="WalletSoldToken", service=SERVICE).inc()

                await rds.xack(RAW_SWAPS_STREAM, GROUP, msg_id)


if __name__ == "__main__":
    asyncio.run(main())
