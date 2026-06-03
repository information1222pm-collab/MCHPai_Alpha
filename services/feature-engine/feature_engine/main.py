"""feature-engine entrypoint.

Listens to token snapshots & wallet buys, assembles a feature context, computes
every registered feature family, writes the vector to ClickHouse + Redis, and
emits ``AttentionSpike`` when attention velocity crosses threshold.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

import orjson

from mchpai_common.config import settings
from mchpai_common.database import get_clickhouse, get_redis
from mchpai_common.events import Envelope, EventBus
from mchpai_common.events.subjects import TOKEN_SNAPSHOT, WALLET_BOUGHT
from mchpai_common.events.types import AttentionSpike, EventType
from mchpai_common.logging import configure as configure_logging, get_logger
from mchpai_common.metrics import FEATURE_COMPUTE_LATENCY, start_metrics_server

from .families import compute_all

SERVICE = "feature-engine"
ATTENTION_VELOCITY_THRESHOLD = 0.5


async def build_context(rds, mint: str, payload: dict) -> dict:
    """Assemble the feature context for a mint from event + cached state."""
    raw = await rds.get(f"feat:ctx:{mint}")
    ctx: dict = orjson.loads(raw) if raw else {}
    ctx.update(payload)
    return ctx


async def main() -> None:
    configure_logging(level=settings.log_level, fmt=settings.log_format, service=SERVICE)
    log = get_logger(SERVICE)
    start_metrics_server(settings.prometheus_port)

    rds = get_redis()
    ch = get_clickhouse()
    bus = await EventBus(settings.nats_url, producer=SERVICE).connect()
    await bus.ensure_streams()

    async def on_snapshot(env: Envelope) -> None:
        mint = env.payload.get("mint")
        if not mint:
            return
        t0 = time.perf_counter()
        ctx = await build_context(rds, mint, env.payload)
        features = compute_all(ctx)
        FEATURE_COMPUTE_LATENCY.observe((time.perf_counter() - t0) * 1000)

        # Serve-side cache + analytical store.
        await rds.set(f"feat:vec:{mint}", orjson.dumps(features).decode(), ex=3600)
        try:
            ch.insert(
                "feature_vectors",
                [[datetime.now(timezone.utc), "token", mint, "all", features]],
                column_names=["ts", "entity_type", "entity_id", "feature_set", "features"],
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("clickhouse.insert_failed", error=str(exc))

        vel = features.get("attention.attention_velocity", 0.0)
        if vel >= ATTENTION_VELOCITY_THRESHOLD:
            await bus.publish(
                EventType.ATTENTION_SPIKE,
                AttentionSpike(
                    mint=mint,
                    attention=features.get("attention.attention", 0.0),
                    velocity=vel,
                    entropy=features.get("entropy.buyer_entropy", 0.0),
                    r0=features.get("attention.r0", 0.0),
                ),
                partition_key=mint,
            )
            log.info("attention.spike", mint=mint, velocity=vel)

    await bus.subscribe(TOKEN_SNAPSHOT, on_snapshot, durable=f"{SERVICE}.snapshot")
    await bus.subscribe(WALLET_BOUGHT, on_snapshot, durable=f"{SERVICE}.bought")
    log.info("feature-engine.started")
    await bus.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
