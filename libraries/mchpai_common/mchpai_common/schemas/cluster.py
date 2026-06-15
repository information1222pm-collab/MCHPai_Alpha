"""Wallet cluster schema (coordinated smart-money groups)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Cluster(BaseModel):
    id: str
    members: list[str] = Field(default_factory=list)
    cluster_score: float = 0.0       # 0..100
    size: int = 0
    method: str = "louvain"          # louvain | connected_components | funding
    label: str | None = None
    detected_at: datetime | None = None

    # Evidence that this is a real coordinated group, not coincidence.
    shared_funder: str | None = None
    co_buy_lift: float | None = None  # observed co-buy rate / random baseline
    metadata: dict = Field(default_factory=dict)
