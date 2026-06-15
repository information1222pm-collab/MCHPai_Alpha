"""alert-engine entrypoint."""

from __future__ import annotations

import asyncio

from mchpai_common.config import settings
from mchpai_common.events import Envelope, EventBus
from mchpai_common.events.subjects import BUY_SIGNAL, CLUSTER_DETECTED
from mchpai_common.logging import configure as configure_logging, get_logger

from .channels import build_channels

SERVICE = "alert-engine"


async def main() -> None:
    configure_logging(level=settings.log_level, fmt=settings.log_format, service=SERVICE)
    log = get_logger(SERVICE)
    channels = build_channels()
    bus = await EventBus(settings.nats_url, producer=SERVICE).connect()
    await bus.ensure_streams()

    async def fan_out(title: str, body: str) -> None:
        for ch in channels:
            try:
                await ch.send(title, body)
            except Exception as exc:  # noqa: BLE001
                log.warning("alert.send_failed", channel=ch.name, error=str(exc))

    async def on_buy(env: Envelope) -> None:
        p = env.payload
        await fan_out(
            "🚨 BUY SIGNAL",
            f"mint `{p['mint']}` · p={p.get('buy_probability'):.2f} · "
            f"EV={p.get('expected_value'):.0f}bps · risk={p.get('risk_score'):.0f}",
        )

    async def on_cluster(env: Envelope) -> None:
        p = env.payload
        await fan_out(
            "🕸️ CLUSTER DETECTED",
            f"size={len(p.get('members', []))} · score={p.get('cluster_score'):.0f}"
            + (f" · funder `{p['shared_funder']}`" if p.get("shared_funder") else ""),
        )

    await bus.subscribe(BUY_SIGNAL, on_buy, durable=f"{SERVICE}.buy")
    await bus.subscribe(CLUSTER_DETECTED, on_cluster, durable=f"{SERVICE}.cluster")
    log.info("alert-engine.started", channels=[c.name for c in channels])
    await bus.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
