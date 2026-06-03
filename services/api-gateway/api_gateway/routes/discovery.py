"""Dynamic memecoin discovery feed.

Surfaces freshly created tokens that smart money is already touching, ranked by a
blend of recency, attention, and the alpha of the wallets buying them.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/new")
async def newly_discovered(request: Request, limit: int = 50, max_age_minutes: int = 120) -> dict:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT t.mint, t.symbol, t.name, t.source, t.created_at, t.risk_score,
                   p.buy_probability, p.expected_value
            FROM tokens t
            LEFT JOIN LATERAL (
                SELECT buy_probability, expected_value FROM predictions
                WHERE mint = t.mint ORDER BY created_at DESC LIMIT 1
            ) p ON true
            WHERE t.created_at > now() - ($2 || ' minutes')::interval
            ORDER BY COALESCE(p.expected_value, 0) DESC, t.created_at DESC
            LIMIT $1
            """,
            limit, str(max_age_minutes),
        )
    return {"tokens": [dict(r) for r in rows]}
