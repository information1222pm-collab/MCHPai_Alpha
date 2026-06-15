"""Token safety heuristics — the cheap, deterministic part of the risk model.

The ML risk model refines this, but these structural flags are fast, explainable,
and catch the obvious rugs (live mint/freeze authority, un-burned LP, whale
concentration). Returns reasons so alerts/UX can explain *why* something scored.
"""

from __future__ import annotations

from ..schemas.scores import RiskAssessment
from ..schemas.token import Token


def token_safety_flags(token: Token, *, top_holder_pct: float | None = None) -> list[str]:
    reasons: list[str] = []
    if token.mint_authority:
        reasons.append("mint_authority_active")
    if token.freeze_authority:
        reasons.append("freeze_authority_active")
    if token.lp_burned is False:
        reasons.append("lp_not_burned")
    if top_holder_pct is not None and top_holder_pct > 0.30:
        reasons.append(f"top_holder_concentration={top_holder_pct:.0%}")
    return reasons


def basic_risk_score(token: Token, *, top_holder_pct: float | None = None) -> RiskAssessment:
    """A 0..100 structural risk estimate (higher = riskier)."""
    score = 10.0
    if token.mint_authority:
        score += 30
    if token.freeze_authority:
        score += 25
    if token.lp_burned is False:
        score += 20
    if top_holder_pct is not None:
        score += min(25.0, top_holder_pct * 50.0)

    return RiskAssessment(
        mint=token.mint,
        risk_score=min(100.0, score),
        mint_authority_active=bool(token.mint_authority),
        freeze_authority_active=bool(token.freeze_authority),
        lp_burned=token.lp_burned,
        top_holder_pct=top_holder_pct,
        reasons=token_safety_flags(token, top_holder_pct=top_holder_pct),
    )
