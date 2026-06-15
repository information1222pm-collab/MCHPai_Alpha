"""Execution schemas: orders into the engine, fills + positions out."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .common import Side


class Order(BaseModel):
    """A sized intent handed to the Rust execution engine."""

    id: str
    mint: str
    side: Side = Side.buy
    size_sol: float
    max_slippage_bps: int = 300
    jito_tip_lamports: int | None = None
    source_signal: int | None = None       # predictions.id
    expected_value_bps: float | None = None
    risk_score: float | None = None
    created_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)


class Fill(BaseModel):
    position_id: str
    signature: str | None = None
    side: Side
    sol_amount: float
    token_amount: float
    landed_slot: int | None = None
    jito_bundle: str | None = None
    latency_ms: int | None = None
    created_at: datetime | None = None


class Position(BaseModel):
    id: str
    mint: str
    status: str = "open"                    # open | closed | failed
    entry_sol: float | None = None
    size_sol: float | None = None
    token_amount: float | None = None
    exit_sol: float | None = None
    pnl_sol: float | None = None
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    source_signal: int | None = None
    metadata: dict = Field(default_factory=dict)
