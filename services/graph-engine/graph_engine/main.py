"""graph-engine entrypoint.

Two responsibilities:
  * Real-time: consume wallet buys → write BOUGHT edges, link co-buyers.
  * Periodic: run cluster detection, validate coordination, emit ClusterDetected.
"""

from __future__ import annotations

import asyncio
import uuid

from mchpai_common.config import settings
from mchpai_common.database import get_pg_pool
from mchpai_common.events import Envelope, EventBus
from mchpai_common.events.subjects import WALLET_BOUGHT
from mchpai_common.events.types import ClusterDetected, EventType
from mchpai_common.logging import configure as configure_logging, get_logger

from . import clustering, graph

SERVICE = "graph-engine"
DETECT_INTERVAL_SECONDS = 300
MIN_CLUSTER_SIZE = 3


async def persist_cluster(pool, cid: str, members: list[str], score: float, funder: str | None) -> None:
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO clusters (id, cluster_score, size, method, metadata) "
                "VALUES ($1,$2,$3,'louvain',$4)",
                cid, score, len(members), {"shared_funder": funder} if funder else {},
            )
            for addr in members:
                await conn.execute(
                    "INSERT INTO wallets (address) VALUES ($1) ON CONFLICT DO NOTHING", addr
                )
                await conn.execute(
                    "INSERT INTO cluster_members (cluster_id, address) VALUES ($1,$2) "
                    "ON CONFLICT DO NOTHING",
                    cid, addr,
                )


async def detection_loop(bus: EventBus, pool, log) -> None:
    while True:
        await asyncio.sleep(DETECT_INTERVAL_SECONDS)
        try:
            communities = await clustering.detect_communities()
        except Exception as exc:  # noqa: BLE001
            log.warning("clustering.failed", error=str(exc))
            continue
        for _cid, members in communities.items():
            if len(members) < MIN_CLUSTER_SIZE:
                continue
            funder = await clustering.shared_funder(members)
            # Coordination boosts the score; a shared funder is strong evidence.
            score = min(100.0, 40.0 + (30.0 if funder else 0.0) + min(30.0, len(members) * 2.0))
            cluster_id = str(uuid.uuid4())
            await persist_cluster(pool, cluster_id, members, score, funder)
            await bus.publish(
                EventType.CLUSTER_DETECTED,
                ClusterDetected(cluster_id=cluster_id, members=members,
                                cluster_score=score, shared_funder=funder),
            )
            log.info("cluster.detected", cluster_id=cluster_id, size=len(members),
                     score=score, shared_funder=bool(funder))


async def main() -> None:
    configure_logging(level=settings.log_level, fmt=settings.log_format, service=SERVICE)
    log = get_logger(SERVICE)

    pool = await get_pg_pool()
    bus = await EventBus(settings.nats_url, producer=SERVICE).connect()
    await bus.ensure_streams()

    async def on_bought(env: Envelope) -> None:
        p = env.payload
        ts = p.get("slot") or 0
        await graph.upsert_bought(p["wallet"], p["mint"], float(p.get("sol_amount", 0)), ts)
        await graph.link_co_buyers(p["mint"])

    await bus.subscribe(WALLET_BOUGHT, on_bought, durable=f"{SERVICE}.bought")
    log.info("graph-engine.started")
    await detection_loop(bus, pool, log)


if __name__ == "__main__":
    asyncio.run(main())
