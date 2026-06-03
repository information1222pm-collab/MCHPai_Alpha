"""Wallet endpoints: profile + alpha score."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("/{address}")
async def get_wallet(address: str, request: Request) -> dict:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        wallet = await conn.fetchrow("SELECT * FROM wallets WHERE address=$1", address)
        if not wallet:
            raise HTTPException(404, "wallet not found")
        profile = await conn.fetchrow("SELECT * FROM wallet_profiles WHERE address=$1", address)
        score = await conn.fetchrow("SELECT * FROM wallet_scores WHERE address=$1", address)
    return {
        "wallet": dict(wallet),
        "profile": dict(profile) if profile else None,
        "score": dict(score) if score else None,
    }


@router.get("")
async def top_wallets(request: Request, limit: int = 50) -> dict:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT address, wallet_alpha_score FROM wallet_scores "
            "ORDER BY wallet_alpha_score DESC NULLS LAST LIMIT $1",
            limit,
        )
    return {"wallets": [dict(r) for r in rows]}
