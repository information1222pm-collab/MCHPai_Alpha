"""Normalized swap/trade schema (the atomic on-chain action)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from .common import Side


class Trade(BaseModel):
    signature: str
    wallet: str
    mint: str
    side: Side
    sol_amount: float
    token_amount: float
    price_sol: float | None = None
    program: str | None = None
    slot: int | None = None
    block_time: datetime | None = None
