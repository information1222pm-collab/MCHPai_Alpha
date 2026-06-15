"""Neo4j (graph intelligence) async driver."""

from __future__ import annotations

from neo4j import AsyncDriver, AsyncGraphDatabase

from ..config import settings

_driver: AsyncDriver | None = None


def get_neo4j() -> AsyncDriver:
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            max_connection_pool_size=50,
        )
    return _driver
