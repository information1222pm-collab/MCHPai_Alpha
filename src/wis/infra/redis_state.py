"""Redis — the hot, online view of latest ``wallet_state(t)``.

Redis serves the most-recent per-wallet summary with sub-millisecond reads for
online consumers. It is a *derived* store: its content is a pure function of the
projected world (:func:`wallet_state_blobs`), so "reproduce identical results"
here means the blobs read back must equal the blobs the oracle produced.

The redis client is imported lazily so the module loads without the extra.
"""

from __future__ import annotations

from wis.infra.projection_rows import wallet_state_blobs
from wis.projections.wallet_projector import WalletWorld

_HASH_KEY = "wis:wallet_state"


class RedisStateStore:
    def __init__(self, url: str = "redis://localhost:6379/0", *, hash_key: str = _HASH_KEY) -> None:
        import redis  # lazy

        self._r = redis.Redis.from_url(url, decode_responses=True)
        self._key = hash_key

    def write_world(self, world: WalletWorld) -> int:
        """Upsert every wallet's latest-state blob. Returns wallets written."""
        blobs = wallet_state_blobs(world)
        if blobs:
            self._r.hset(self._key, mapping=blobs)
        return len(blobs)

    def get(self, address: str) -> str | None:
        return self._r.hget(self._key, address)

    def all(self) -> dict[str, str]:
        return dict(self._r.hgetall(self._key))

    def clear(self) -> None:
        self._r.delete(self._key)
