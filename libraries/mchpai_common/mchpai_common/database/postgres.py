"""PostgreSQL (truth DB) async pool."""

from __future__ import annotations

import asyncpg

from ..config import settings

_pool: asyncpg.Pool | None = None


async def get_pg_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=settings.postgres_url,
            min_size=2,
            max_size=20,
            command_timeout=30,
            server_settings={"search_path": "mchpai,public"},
        )
    return _pool
