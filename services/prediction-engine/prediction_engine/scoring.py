"""The five headline scores.

This module is deliberately model-light: it defines *transparent, explainable*
baselines for every score so the platform is fully functional before any ML model
is trained. The ML models (models/) later override ``buy_probability`` and parts
of ``risk_score`` — but these baselines remain the fallback and the sanity check.
"""

from __future__ import annotations

import numpy as np

from mchpai_common.forecasting import expected_value as ev_bps
from mchpai_common.schemas.wallet import WalletProfile

# population priors for empirical-Bayes shrinkage of thin-sample wallets
PRIOR_WIN_RATE = 0.45
PRIOR_STRENGTH = 10  # pseudo-trades


def wallet_alpha_score(p: WalletProfile) -> tuple[float, dict[str, float]]:
    """0..100 composite of the six behavioral axes, shrunk for small samples.

    Win rate is shrunk toward the population prior so a 2-for-2 wallet does not
    outrank a 180-for-300 wallet. ROI is winsorized to tame outliers.
    """
    n = p.closed_trades
    shrunk_wr = (p.win_rate * n + PRIOR_WIN_RATE * PRIOR_STRENGTH) / (n + PRIOR_STRENGTH)
    roi_w = float(np.clip(p.roi, -1.0, 5.0)) / 5.0  # → ~[-0.2, 1.0]

    components = {
        "roi": float(np.clip(roi_w, 0, 1)),
        "win_rate": float(shrunk_wr),
        "consistency": float(p.profit_consistency),
        "conviction": float(p.conviction),
        # reward decisive but not reckless hold times (penalize <30s flips)
        "hold_quality": float(np.clip(p.avg_hold_seconds / 3600.0, 0, 1)),
        "risk_penalty": float(1.0 - np.clip(p.risk, 0, 1)),
    }
    weights = {
        "roi": 0.30, "win_rate": 0.25, "consistency": 0.15,
        "conviction": 0.12, "hold_quality": 0.08, "risk_penalty": 0.10,
    }
    raw = sum(components[k] * weights[k] for k in weights)
    # sample-size confidence multiplier
    confidence = n / (n + PRIOR_STRENGTH)
    score = 100.0 * raw * (0.5 + 0.5 * confidence)
    return float(np.clip(score, 0, 100)), components


def cluster_score(member_alphas: list[float], co_buy_lift: float, has_shared_funder: bool) -> float:
    """0..100. Strong clusters = high-alpha members + non-coincidental co-buys."""
    if not member_alphas:
        return 0.0
    member_quality = float(np.mean(member_alphas))           # 0..100
    coordination = float(np.clip(co_buy_lift / 5.0, 0, 1))    # lift of 5x → max
    funder_bonus = 15.0 if has_shared_funder else 0.0
    return float(np.clip(0.6 * member_quality + 30.0 * coordination + funder_bonus, 0, 100))


def buy_probability_baseline(features: dict[str, float]) -> float:
    """Transparent logistic baseline over key features (pre-ML)."""
    z = (
        -2.0
        + 1.4 * features.get("alpha_buyers_norm", 0.0)
        + 1.1 * features.get("cluster.cluster_score_norm", 0.0)
        + 0.8 * features.get("attention.r0_norm", 0.0)
        + 0.6 * features.get("spread.flow_imbalance", 0.0)
        + 0.5 * features.get("entropy.buyer_entropy", 0.0)
    )
    return float(1.0 / (1.0 + np.exp(-z)))


def expected_value_bps(
    buy_probability: float, *, up_bps: float = 600.0, down_bps: float = 350.0,
    fee_bps: float = 30.0, slippage_bps: float = 80.0,
) -> float:
    """EV in bps net of fees + expected slippage."""
    return ev_bps(buy_probability, up_bps, down_bps, cost_bps=fee_bps + slippage_bps)
