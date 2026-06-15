"""ranking-engine entrypoint — periodic leaderboard refresh."""

from __future__ import annotations

import asyncio

import orjson

from mchpai_common.config import settings
from mchpai_common.database import get_pg_pool, get_redis
from mchpai_common.logging import configure as configure_logging, get_logger

SERVICE = "ranking-engine"
REFRESH_SECONDS = 60
WALLET_LB_KEY = "leaderboard:wallets"   # Redis ZSET
CLUSTER_LB_KEY = "leaderboard:clusters"


async def refresh(pool, rds, log) -> None:
    async with pool.acquire() as conn:
        wallets = await conn.fetch(
            "SELECT address, wallet_alpha_score FROM wallet_scores "
            "ORDER BY wallet_alpha_score DESC NULLS LAST LIMIT 500"
        )
        clusters = await conn.fetch(
            "SELECT id::text AS id, cluster_score FROM clusters "
            "ORDER BY cluster_score DESC NULLS LAST LIMIT 200"
        )

    if wallets:
        await rds.delete(WALLET_LB_KEY)
        await rds.zadd(WALLET_LB_KEY, {w["address"]: float(w["wallet_alpha_score"] or 0) for w in wallets})
    if clusters:
        await rds.delete(CLUSTER_LB_KEY)
        await rds.zadd(CLUSTER_LB_KEY, {c["id"]: float(c["cluster_score"] or 0) for c in clusters})

    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO leaderboard_snapshots (rankings) VALUES ($1)",
            orjson.dumps([dict(w) for w in wallets]).decode(),
        )
    log.info("leaderboard.refreshed", wallets=len(wallets), clusters=len(clusters))


async def main() -> None:
    configure_logging(level=settings.log_level, fmt=settings.log_format, service=SERVICE)
    log = get_logger(SERVICE)
    pool = await get_pg_pool()
    rds = get_redis()
    log.info("ranking-engine.started")
    while True:
        try:
            await refresh(pool, rds, log)
        except Exception as exc:  # noqa: BLE001
            log.warning("refresh.failed", error=str(exc))
        await asyncio.sleep(REFRESH_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
