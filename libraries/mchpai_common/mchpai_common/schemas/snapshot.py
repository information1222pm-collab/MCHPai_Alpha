"""Multi-resolution token snapshot schema.

Snapshots are the time-series backbone. We capture the same token at multiple
window resolutions (5s/15s/30s/60s) so future models can choose their temporal
granularity. Each snapshot is one ordered step in a token's life sequence.

Four metric groups (per the Phase-1 spec): market, participation, intelligence,
safety. Everything is optional-friendly so partial data never blocks a snapshot.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Window(str, Enum):
    s5 = "5s"
    s15 = "15s"
    s30 = "30s"
    s60 = "60s"

    @property
    def seconds(self) -> int:
        return {"5s": 5, "15s": 15, "30s": 30, "60s": 60}[self.value]


class LifecyclePhase(str, Enum):
    """Ordered phases of a token's life — the labels for sequence learning."""

    birth = "birth"               # just created, pre-traction
    growth = "growth"             # accelerating buys, rising liquidity
    viral = "viral"               # peak attention / R0 > 1, parabolic
    distribution = "distribution" # smart money exiting, flow turning
    death = "death"               # liquidity gone / rugged / abandoned


class TokenSnapshot(BaseModel):
    mint: str
    window: Window
    ts: datetime                  # window close time (aligned to window boundary)
    seq: int                      # monotonically increasing index within (mint,window)
    age_seconds: float            # since token birth — anchors the sequence
    phase: LifecyclePhase | None = None

    # --- market ---
    price_sol: float | None = None
    open_sol: float | None = None
    high_sol: float | None = None
    low_sol: float | None = None
    close_sol: float | None = None
    volume_sol: float = 0.0
    liquidity_sol: float | None = None
    market_cap_sol: float | None = None

    # --- participation ---
    buyers: int = 0
    sellers: int = 0
    unique_traders: int = 0
    holders: int | None = None
    txns: int = 0

    # --- intelligence ---
    entropy: float | None = None          # buyer capital entropy
    r0: float | None = None               # epidemiological reproduction
    smart_money_ratio: float | None = None  # alpha-weighted buy share
    cluster_ratio: float | None = None      # share of volume from known clusters
    net_flow_sol: float = 0.0             # buy_vol - sell_vol

    # --- safety ---
    top_holder_pct: float | None = None
    holder_concentration_gini: float | None = None
    lp_health: float | None = None        # 0..1 (burned + locked + depth)

    features: dict[str, float] = Field(default_factory=dict)
