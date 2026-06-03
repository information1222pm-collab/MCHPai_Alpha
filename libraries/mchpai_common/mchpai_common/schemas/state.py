"""Temporal state schemas — entities as evolving sequences, not static rows.

The Phase-2 doctrine: record ``state(t)`` for every entity so future temporal
models (TFT, temporal GNN, wallet/creator transformers) consume *movies*, not
snapshots. Each state carries ``seq`` + ``ts`` so it slots into an ordered
trajectory. All are append-only; we never overwrite history.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WalletState(BaseModel):
    """wallet_state(t) — the wallet's position & behavior at one instant."""

    address: str
    ts: datetime
    seq: int
    realized_pnl_sol: float = 0.0
    unrealized_pnl_sol: float = 0.0      # requires marks; 0 when unknown
    exposure_sol: float = 0.0            # open cost basis across all mints
    open_positions: int = 0
    position_concentration: float = 0.0  # Herfindahl of exposure across mints (0..1)
    conviction: float = 0.0              # latest position size / running avg
    scaling: float = 0.0                 # recent add-to-position tendency (-1..1)
    cumulative_volume_sol: float = 0.0
    trade_count: int = 0


class CreatorState(BaseModel):
    """creator_state(t) — a creator's evolving track record."""

    creator: str
    ts: datetime
    seq: int
    launches_so_far: int = 0
    rugs_so_far: int = 0
    rug_rate: float = 0.0
    best_multiple_so_far: float = 1.0
    alive_count: int = 0
    cumulative_volume_sol: float = 0.0


class GraphState(BaseModel):
    """graph(t) — a lightweight metric snapshot of the evolving wallet graph."""

    ts: datetime
    seq: int
    wallets: int = 0
    co_buy_edges: int = 0
    funded_edges: int = 0
    transfer_edges: int = 0
    clusters: int = 0
    top_cluster_score: float = 0.0
    density: float = 0.0                  # edges / wallets
    new_edges_delta: int = 0


class TokenTrajectory(BaseModel):
    """The ordered life of a token: birth → growth → viral → distribution → death.

    A thin wrapper over an ordered snapshot sequence with helpers to materialize
    the matrix form temporal models expect and to extract phase transitions.
    """

    mint: str
    birth_ts: datetime
    seq_len: int = 0
    phases_seen: list[str] = Field(default_factory=list)
    # snapshots are stored/queried in ClickHouse; this carries summary + the
    # ordered (seq, age, phase) skeleton for quick trajectory reasoning.
    steps: list[dict] = Field(default_factory=list)  # [{seq, age_seconds, phase, price_sol}]
