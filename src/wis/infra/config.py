"""Environment-driven configuration for infrastructure adapters.

Dependency-free (reads ``os.environ`` directly) so it can be imported anywhere
without pulling in a settings framework. Values mirror ``.env.example``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


@dataclass(frozen=True, slots=True)
class Settings:
    pg_dsn: str
    clickhouse_url: str
    redis_url: str
    neo4j_uri: str
    neo4j_auth: str
    nats_url: str
    event_stream: str
    minio_endpoint: str
    minio_bucket: str

    @staticmethod
    def from_env() -> Settings:
        pg = (
            f"postgresql://{_env('WIS_PG_USER', 'wis')}:{_env('WIS_PG_PASSWORD', 'wis')}"
            f"@{_env('WIS_PG_HOST', 'localhost')}:{_env('WIS_PG_PORT', '5432')}"
            f"/{_env('WIS_PG_DB', 'wis')}"
        )
        return Settings(
            pg_dsn=pg,
            clickhouse_url=(
                f"http://{_env('WIS_CLICKHOUSE_HOST', 'localhost')}:{_env('WIS_CLICKHOUSE_PORT', '8123')}"
            ),
            redis_url=_env("WIS_REDIS_URL", "redis://localhost:6379/0"),
            neo4j_uri=_env("WIS_NEO4J_URI", "bolt://localhost:7687"),
            neo4j_auth=_env("WIS_NEO4J_AUTH", "neo4j/wisgraphpw"),
            nats_url=_env("WIS_NATS_URL", "nats://localhost:4222"),
            event_stream=_env("WIS_EVENT_STREAM", "wis-events"),
            minio_endpoint=_env("WIS_MINIO_ENDPOINT", "localhost:9000"),
            minio_bucket=_env("WIS_MINIO_BUCKET", "wis-replay"),
        )
