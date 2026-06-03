"""Token birth schema — sacred and immutable.

A token is born exactly once. Its birth facts (slot, timestamp, creator,
launchpad, initial liquidity/mcap) are recorded immutably and never overwritten.
Losing a birth means losing the anchor of an entire trajectory, so the registry
is append-only and idempotent.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from .common import TokenSource


class TokenBirth(BaseModel):
    mint: str
    birth_slot: int | None = None
    birth_timestamp: datetime
    creator: str | None = None
    launchpad: TokenSource = TokenSource.unknown
    initial_liquidity_sol: float | None = None
    initial_market_cap_sol: float | None = None
    first_signature: str | None = None
