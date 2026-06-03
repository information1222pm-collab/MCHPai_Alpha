"""creator-intelligence entrypoint — periodic creator profiling loop."""

from __future__ import annotations

import asyncio
import json

from mchpai_common.config import settings
from mchpai_common.creators import TokenLaunch, build_creator_profile
from mchpai_common.database import get_clickhouse, get_pg_pool
from mchpai_common.logging import configure as configure_logging, get_logger

SERVICE = "creator-intelligence"
INTERVAL_SECONDS = 600
CREATORS_PER_CYCLE = 200


async def creators_to_score(pool) -> list[str]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT creator FROM tokens
            WHERE creator IS NOT NULL
            GROUP BY creator
            ORDER BY max(created_at) DESC
            LIMIT $1
            """,
            CREATORS_PER_CYCLE,
        )
    return [r["creator"] for r in rows]


async def launches_for(pool, ch, creator: str) -> list[TokenLaunch]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT t.mint,
                   COALESCE(g.outcome, 'pending') AS outcome,
                   COALESCE(g.max_multiple, 1.0) AS max_multiple,
                   COALESCE(g.survival_seconds, 0) AS survival_seconds,
                   COALESCE(g.holder_retention, 0) AS holder_retention
            FROM tokens t
            LEFT JOIN ground_truth g ON g.mint = t.mint
            WHERE t.creator = $1
            """,
            creator,
        )
    launches: list[TokenLaunch] = []
    for r in rows:
        vol, total_buyers, repeat_buyers = 0.0, 0, 0
        try:
            res = ch.query(
                """
                SELECT sum(sol_amount) AS vol,
                       uniqExact(wallet) AS buyers,
                       countIf(c > 1) AS repeat_buyers
                FROM (
                    SELECT wallet, count() AS c, sum(sol_amount) AS sol_amount
                    FROM trades WHERE mint = %(m)s AND side = 'buy' GROUP BY wallet
                )
                """,
                parameters={"m": r["mint"]},
            )
            if res.result_rows:
                row = res.result_rows[0]
                vol = float(row[0] or 0.0)
                total_buyers = int(row[1] or 0)
                repeat_buyers = int(row[2] or 0)
        except Exception:
            pass
        launches.append(
            TokenLaunch(
                mint=r["mint"],
                rugged=(r["outcome"] == "rugged"),
                max_multiple=float(r["max_multiple"]),
                survival_seconds=float(r["survival_seconds"]),
                holder_retention=float(r["holder_retention"]),
                volume_sol=vol,
                total_buyers=total_buyers,
                repeat_buyers=repeat_buyers,
            )
        )
    return launches


async def upsert(pool, p) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO creator_profiles
              (creator, launch_count, rug_count, rug_rate, best_multiple, median_multiple,
               median_survival_seconds, avg_holder_retention, volume_generated_sol,
               repeat_buyer_rate, creator_score, components, updated_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12, now())
            ON CONFLICT (creator) DO UPDATE SET
              launch_count=EXCLUDED.launch_count, rug_count=EXCLUDED.rug_count,
              rug_rate=EXCLUDED.rug_rate, best_multiple=EXCLUDED.best_multiple,
              median_multiple=EXCLUDED.median_multiple,
              median_survival_seconds=EXCLUDED.median_survival_seconds,
              avg_holder_retention=EXCLUDED.avg_holder_retention,
              volume_generated_sol=EXCLUDED.volume_generated_sol,
              repeat_buyer_rate=EXCLUDED.repeat_buyer_rate,
              creator_score=EXCLUDED.creator_score, components=EXCLUDED.components,
              updated_at=now()
            """,
            p.creator, p.launch_count, p.rug_count, p.rug_rate, p.best_multiple,
            p.median_multiple, p.median_survival_seconds, p.avg_holder_retention,
            p.volume_generated_sol, p.repeat_buyer_rate, p.creator_score,
            json.dumps(p.components),
        )


async def main() -> None:
    configure_logging(level=settings.log_level, fmt=settings.log_format, service=SERVICE)
    log = get_logger(SERVICE)
    pool = await get_pg_pool()
    ch = get_clickhouse()
    log.info("creator-intelligence.started")

    while True:
        try:
            creators = await creators_to_score(pool)
            for creator in creators:
                launches = await launches_for(pool, ch, creator)
                profile = build_creator_profile(creator, launches)
                await upsert(pool, profile)
            log.info("creator.cycle", scored=len(creators))
        except Exception as exc:  # noqa: BLE001
            log.warning("creator.cycle_failed", error=str(exc))
        await asyncio.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
