"""ClickHouse (time-series / analytics) client."""

from __future__ import annotations

import clickhouse_connect

from ..config import settings

_client = None


def get_clickhouse():
    global _client
    if _client is None:
        _client = clickhouse_connect.get_client(
            host=settings.clickhouse_host,
            port=settings.clickhouse_http_port,
            username=settings.clickhouse_user,
            password=settings.clickhouse_password,
            database=settings.clickhouse_db,
        )
    return _client
