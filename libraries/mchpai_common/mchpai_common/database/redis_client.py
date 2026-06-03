"""Redis (hot cache / low-latency shared state) async client."""

from __future__ import annotations

import redis.asyncio as redis

from ..config import settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


# Well-known keys shared with the Rust engine.
KEY_EXEC_PAUSED = "exec:paused"              # global kill-switch flag
KEY_TOKEN_META = "token:meta:{mint}"         # cached token metadata
KEY_WALLET_HOT = "wallet:hot:{address}"      # rolling hot wallet state
KEY_WALLET_SCORE = "score:wallet:{address}"  # cached alpha score
KEY_PREDICTION = "pred:{mint}"               # latest prediction (decision cache)
