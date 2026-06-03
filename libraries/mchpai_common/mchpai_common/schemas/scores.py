"""Scoring schemas — the five headline scores of the platform.

    wallet_alpha_score   (0..100)  how reliably a wallet generates alpha
    cluster_score        (0..100)  strength/quality of a coordinated cluster
    buy_probability      (0..1)    P(smart money buys this token in the window)
    expected_value       (bps)     expected return of copying, net of costs
    risk_score           (0..100)  rug/honeypot/volatility risk of the token
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WalletScore(BaseModel):
    address: str
    wallet_alpha_score: float = 0.0      # 0..100
    components: dict[str, float] = Field(default_factory=dict)
    computed_at: datetime | None = None


class ClusterScore(BaseModel):
    cluster_id: str
    cluster_score: float = 0.0           # 0..100
    components: dict[str, float] = Field(default_factory=dict)
    computed_at: datetime | None = None


class RiskAssessment(BaseModel):
    mint: str
    risk_score: float = 0.0             # 0..100 (higher = riskier)
    mint_authority_active: bool | None = None
    freeze_authority_active: bool | None = None
    lp_burned: bool | None = None
    top_holder_pct: float | None = None
    honeypot: bool | None = None
    reasons: list[str] = Field(default_factory=list)
    computed_at: datetime | None = None


class Prediction(BaseModel):
    """The decision-time output that drives execution."""

    mint: str
    model_version: str = "v0"
    buy_probability: float = 0.0        # 0..1
    expected_value: float = 0.0         # bps, net of fees + slippage
    risk_score: float = 0.0             # 0..100
    alpha_buyers: list[str] = Field(default_factory=list)
    top_cluster_id: str | None = None
    features: dict[str, float] = Field(default_factory=dict)
    created_at: datetime | None = None

    def crosses(self, tau_p: float, tau_ev: float, tau_risk: float) -> bool:
        """Decision gate: all three thresholds must hold to emit a buy signal."""
        return (
            self.buy_probability >= tau_p
            and self.expected_value >= tau_ev
            and self.risk_score <= tau_risk
        )
