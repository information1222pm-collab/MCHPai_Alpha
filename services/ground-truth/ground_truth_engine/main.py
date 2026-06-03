"""ground-truth-engine entrypoint — periodic labeling loop."""

from __future__ import annotations

import asyncio
import json

from mchpai_common.config import settings
from mchpai_common.database import get_clickhouse, get_pg_pool
from mchpai_common.ground_truth import SnapshotPoint, compute_ground_truth
from mchpai_common.logging import configure as configure_logging, get_logger

SERVICE = "ground-truth-engine"
LABEL_INTERVAL_SECONDS = 300
BATCH = 500


async def candidates(pool) -> list[dict]:
    """Tokens that still need (re)labeling: no final label and old enough to score."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT t.mint, t.created_at
            FROM tokens t
            LEFT JOIN ground_truth g ON g.mint = t.mint
            WHERE t.created_at > now() - interval '8 days'
              AND (g.mint IS NULL OR g.is_final = false)
            ORDER BY t.created_at DESC
            LIMIT $1
            """,
            BATCH,
        )
    return [dict(r) for r in rows]


def fetch_sequence(ch, mint: str) -> list[SnapshotPoint]:
    res = ch.query(
        "SELECT age_seconds, close_sol, liquidity_sol, holders "
        "FROM snapshots WHERE mint = %(m)s AND window = '60s' ORDER BY ts",
        parameters={"m": mint},
    )
    return [
        SnapshotPoint(age_seconds=float(r[0]), price_sol=float(r[1]) or None,
                      liquidity_sol=float(r[2]) or None, holders=int(r[3]) or None)
        for r in res.result_rows
    ]


async def upsert(pool, gt) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO ground_truth
              (mint, created_at, reference_price, max_multiple, time_to_max_seconds,
               outcome, rugged_at, survival_seconds, holder_retention, achieved,
               max_multiple_by_horizon, is_final, labeled_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12, now())
            ON CONFLICT (mint) DO UPDATE SET
              reference_price = EXCLUDED.reference_price,
              max_multiple = EXCLUDED.max_multiple,
              time_to_max_seconds = EXCLUDED.time_to_max_seconds,
              outcome = EXCLUDED.outcome,
              rugged_at = EXCLUDED.rugged_at,
              survival_seconds = EXCLUDED.survival_seconds,
              holder_retention = EXCLUDED.holder_retention,
              achieved = EXCLUDED.achieved,
              max_multiple_by_horizon = EXCLUDED.max_multiple_by_horizon,
              is_final = EXCLUDED.is_final,
              labeled_at = now()
            """,
            gt.mint, gt.created_at, gt.reference_price, gt.max_multiple,
            gt.time_to_max_seconds, gt.outcome.value, gt.rugged_at, gt.survival_seconds,
            gt.holder_retention, json.dumps(gt.achieved),
            json.dumps(gt.max_multiple_by_horizon), gt.is_final,
        )


async def main() -> None:
    configure_logging(level=settings.log_level, fmt=settings.log_format, service=SERVICE)
    log = get_logger(SERVICE)
    pool = await get_pg_pool()
    ch = get_clickhouse()
    log.info("ground-truth-engine.started")

    while True:
        try:
            toks = await candidates(pool)
            labeled = 0
            for t in toks:
                points = fetch_sequence(ch, t["mint"])
                if not points:
                    continue
                gt = compute_ground_truth(t["mint"], t["created_at"], points)
                await upsert(pool, gt)
                labeled += 1
            log.info("labeling.cycle", candidates=len(toks), labeled=labeled)
        except Exception as exc:  # noqa: BLE001
            log.warning("labeling.failed", error=str(exc))
        await asyncio.sleep(LABEL_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
