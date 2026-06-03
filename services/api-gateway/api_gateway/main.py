"""api-gateway FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from mchpai_common.config import settings
from mchpai_common.database import get_pg_pool, get_redis
from mchpai_common.logging import configure as configure_logging, get_logger

from .routes import clusters, discovery, signals, wallets
from .ws import router as ws_router

SERVICE = "api-gateway"


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(level=settings.log_level, fmt=settings.log_format, service=SERVICE)
    app.state.pool = await get_pg_pool()
    app.state.redis = get_redis()
    get_logger(SERVICE).info("api-gateway.started")
    yield


app = FastAPI(title="MCHPAI API", version="0.1.0", lifespan=lifespan)

app.include_router(wallets.router, prefix="/wallets", tags=["wallets"])
app.include_router(clusters.router, prefix="/clusters", tags=["clusters"])
app.include_router(signals.router, prefix="/signals", tags=["signals"])
app.include_router(discovery.router, prefix="/discovery", tags=["discovery"])
app.include_router(ws_router, tags=["ws"])


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok", "service": SERVICE, "env": settings.mchpai_env}


@app.get("/stats")
async def stats() -> dict:
    """Observatory progress — the march to 1M snapshots / 10k / 100k tokens."""
    rds = app.state.redis
    snapshots = int(await rds.get("stats:snapshots") or 0)
    tokens = int(await rds.get("stats:tokens") or 0)
    births = int(await rds.get("stats:births") or 0)
    events = int(await rds.get("stats:events") or 0)
    milestones = {
        "snapshots_1M": {"target": 1_000_000, "progress": snapshots / 1_000_000},
        "tokens_10k": {"target": 10_000, "progress": tokens / 10_000},
        "tokens_100k": {"target": 100_000, "progress": tokens / 100_000},
    }
    return {
        "events": events, "snapshots": snapshots, "tokens": tokens, "births": births,
        "milestones": milestones,
    }


@app.get("/leaderboard")
async def leaderboard(limit: int = 50) -> dict:
    rds = app.state.redis
    top = await rds.zrevrange("leaderboard:wallets", 0, limit - 1, withscores=True)
    return {"wallets": [{"address": a, "alpha_score": s} for a, s in top]}


@app.post("/control/pause")
async def pause() -> dict:
    await app.state.redis.set("exec:paused", "1")
    return {"paused": True}


@app.post("/control/resume")
async def resume() -> dict:
    await app.state.redis.delete("exec:paused")
    return {"paused": False}
