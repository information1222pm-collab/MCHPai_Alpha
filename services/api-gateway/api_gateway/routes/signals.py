"""Prediction / signal endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/predictions")
async def recent_predictions(request: Request, limit: int = 100) -> dict:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT mint, buy_probability, expected_value, risk_score, model_version, created_at "
            "FROM predictions ORDER BY created_at DESC LIMIT $1",
            limit,
        )
    return {"predictions": [dict(r) for r in rows]}


@router.get("/predictions/{mint}")
async def latest_prediction(mint: str, request: Request) -> dict:
    rds = request.app.state.redis
    cached = await rds.get(f"pred:{mint}")
    return {"mint": mint, "prediction": cached}
