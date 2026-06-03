"""Datastore client factories.

Thin, lazily-constructed async clients for the five stores. Each returns a
configured handle; pooling/lifecycle is the caller's (services hold one per
process). Keeping these here means a store can be swapped/upgraded in one place.

    postgres  -> truth database          (asyncpg pool)
    clickhouse-> time-series/analytics   (clickhouse-connect)
    neo4j     -> graph intelligence      (neo4j async driver)
    redis     -> hot cache               (redis.asyncio)
    minio     -> feature/model store     (minio S3 client)
"""

from .postgres import get_pg_pool
from .redis_client import get_redis
from .neo4j_client import get_neo4j
from .clickhouse_client import get_clickhouse
from .minio_client import get_minio

__all__ = ["get_pg_pool", "get_redis", "get_neo4j", "get_clickhouse", "get_minio"]
