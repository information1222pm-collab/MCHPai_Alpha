"""strategy-engine entrypoint.

Consumes ``BuySignalGenerated``, applies risk budget + adaptive sizing, checks the
global kill-switch and the daily loss limit, and emits an ``Order`` for the Rust
execution-engine. Honors ``EXECUTION_MODE=paper`` by tagging orders as dry-run.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from mchpai_common.config import settings
from mchpai_common.database import get_redis
from mchpai_common.database.redis_client import KEY_EXEC_PAUSED
from mchpai_common.events import Envelope, EventBus
from mchpai_common.events.subjects import BUY_SIGNAL
from mchpai_common.events.types import EventType
from mchpai_common.logging import configure as configure_logging, get_logger
from mchpai_common.schemas.common import Side
from mchpai_common.schemas.execution import Order

from .sizing import SizingConfig, adaptive_size

SERVICE = "strategy-engine"
ORDER_STREAM = "exec.orders"   # Redis stream the Rust engine consumes


async def current_token_exposure(rds, mint: str) -> float:
    val = await rds.get(f"exposure:{mint}")
    return float(val) if val else 0.0


async def daily_pnl(rds) -> float:
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    val = await rds.get(f"pnl:day:{day}")
    return float(val) if val else 0.0


async def main() -> None:
    configure_logging(level=settings.log_level, fmt=settings.log_format, service=SERVICE)
    log = get_logger(SERVICE)

    rds = get_redis()
    bus = await EventBus(settings.nats_url, producer=SERVICE).connect()
    await bus.ensure_streams()

    cfg = SizingConfig(
        bankroll_sol=settings.bankroll_sol,
        kelly_fraction=settings.kelly_fraction,
        min_ticket_sol=settings.min_ticket_sol,
        max_ticket_sol=settings.max_ticket_sol,
        max_token_exposure_sol=settings.max_token_exposure_sol,
    )

    async def on_signal(env: Envelope) -> None:
        p = env.payload
        mint = p["mint"]

        # --- kill-switches ---
        if await rds.get(KEY_EXEC_PAUSED) == "1":
            log.warning("order.skipped.paused", mint=mint)
            return
        if await daily_pnl(rds) <= -settings.daily_loss_limit_sol:
            await rds.set(KEY_EXEC_PAUSED, "1")
            log.error("daily_loss_limit_hit.pausing")
            return

        exposure = await current_token_exposure(rds, mint)
        conviction = float(p.get("conviction", 0.5))
        size = adaptive_size(
            cfg,
            expected_value_bps=float(p["expected_value"]),
            risk_score=float(p["risk_score"]),
            conviction=conviction,
            current_token_exposure_sol=exposure,
            token_liquidity_sol=float(p.get("liquidity_sol", 0.0)),
        )
        if size <= 0:
            log.info("order.skipped.zero_size", mint=mint)
            return

        order = Order(
            id=str(uuid.uuid4()), mint=mint, side=Side.buy, size_sol=size,
            jito_tip_lamports=settings.jito_tip_lamports,
            source_signal=int(p["signal_id"]) if str(p.get("signal_id", "")).isdigit() else None,
            expected_value_bps=float(p["expected_value"]),
            risk_score=float(p["risk_score"]),
            created_at=datetime.now(timezone.utc),
            metadata={"mode": settings.execution_mode},
        )

        # Hand to the Rust engine via Redis stream (low-latency path)…
        await rds.xadd(ORDER_STREAM, {"data": order.model_dump_json()})
        # …and announce it on the bus for observers/audit.
        await bus.publish(EventType.BUY_SIGNAL_GENERATED, p, partition_key=mint)
        log.info("order.emitted", mint=mint, size_sol=round(size, 4), mode=settings.execution_mode)

    await bus.subscribe(BUY_SIGNAL, on_signal, durable=f"{SERVICE}.signal")
    log.info("strategy-engine.started", mode=settings.execution_mode)
    await bus.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
