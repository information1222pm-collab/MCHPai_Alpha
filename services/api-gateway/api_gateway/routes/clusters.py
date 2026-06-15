"""Cluster endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


@router.get("")
async def list_clusters(request: Request, limit: int = 50) -> dict:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, cluster_score, size, method, detected_at FROM clusters "
            "ORDER BY cluster_score DESC NULLS LAST LIMIT $1",
            limit,
        )
    return {"clusters": [dict(r) for r in rows]}


@router.get("/{cluster_id}")
async def get_cluster(cluster_id: str, request: Request) -> dict:
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        cluster = await conn.fetchrow("SELECT * FROM clusters WHERE id=$1::uuid", cluster_id)
        if not cluster:
            raise HTTPException(404, "cluster not found")
        members = await conn.fetch(
            "SELECT address FROM cluster_members WHERE cluster_id=$1::uuid", cluster_id
        )
    return {"cluster": dict(cluster), "members": [m["address"] for m in members]}
