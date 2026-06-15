"""Wallet domain schemas: identity + behavioral profile."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .common import WalletLabel


class Wallet(BaseModel):
    address: str
    first_seen_at: datetime | None = None
    first_funded_by: str | None = None
    label: WalletLabel = WalletLabel.unknown
    tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class WalletProfile(BaseModel):
    """Behavioral profile over a rolling window.

    These six axes are the foundation of ``wallet_alpha_score``. All ratios are
    computed from FIFO-matched round-trips so that open positions never inflate
    realized performance.
    """

    address: str
    window_days: int = 30
    closed_trades: int = 0

    roi: float = 0.0                 # realized PnL / cost basis
    win_rate: float = 0.0            # 0..1
    avg_hold_seconds: float = 0.0
    conviction: float = 0.0          # 0..1 — sizing relative to bankroll + add-ons
    risk: float = 0.0               # 0..1 — behavioral risk appetite
    profit_consistency: float = 0.0  # 0..1 — inverse coefficient of variation

    realized_pnl_sol: float = 0.0
    computed_at: datetime | None = None
