"""Token domain schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .common import TokenSource


class Token(BaseModel):
    """A token (mint) the platform is aware of."""

    mint: str
    symbol: str | None = None
    name: str | None = None
    decimals: int | None = None
    creator: str | None = None
    source: TokenSource = TokenSource.unknown
    created_at: datetime | None = None
    first_seen_slot: int | None = None

    # Safety-relevant authorities/flags (feed the risk model).
    mint_authority: str | None = None
    freeze_authority: str | None = None
    lp_burned: bool | None = None

    metadata: dict = Field(default_factory=dict)


class TokenSnapshot(BaseModel):
    """A point-in-time market snapshot of a token (high-volume, → ClickHouse)."""

    mint: str
    ts: datetime
    price_sol: float | None = None
    price_usd: float | None = None
    liquidity_sol: float | None = None
    market_cap: float | None = None
    holders: int | None = None
    volume_1m: float | None = None
    buys_1m: int | None = None
    sells_1m: int | None = None
    source: TokenSource = TokenSource.unknown
