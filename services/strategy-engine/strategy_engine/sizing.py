"""Adaptive position sizing — fractional Kelly with safety caps.

    edge      = clamp(EV_bps / 10_000, 0, edge_cap)
    kelly_f   = edge / variance_estimate
    size_sol  = bankroll · kelly_fraction · kelly_f
                         · conviction_multiplier
                         · (1 - risk_score/100)
    size_sol  = clamp(size_sol, min_ticket, min(max_ticket, pct_of_liquidity))

Conviction comes from the copied wallet/cluster: we lean in harder when strong,
proven money is leading the trade.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class SizingConfig:
    bankroll_sol: float
    kelly_fraction: float = 0.25
    min_ticket_sol: float = 0.05
    max_ticket_sol: float = 2.0
    max_token_exposure_sol: float = 4.0
    edge_cap: float = 0.10            # cap raw edge at 1000 bps
    variance_estimate: float = 0.25   # outcome variance proxy
    liquidity_fraction_cap: float = 0.02  # never exceed 2% of pool liquidity


def adaptive_size(
    cfg: SizingConfig,
    *,
    expected_value_bps: float,
    risk_score: float,
    conviction: float = 0.5,
    current_token_exposure_sol: float = 0.0,
    token_liquidity_sol: float = 0.0,
) -> float:
    edge = float(np.clip(expected_value_bps / 10_000.0, 0.0, cfg.edge_cap))
    if edge <= 0:
        return 0.0

    kelly_f = edge / max(cfg.variance_estimate, 1e-6)
    conviction_mult = 0.5 + float(np.clip(conviction, 0, 1))  # 0.5x .. 1.5x
    risk_mult = 1.0 - float(np.clip(risk_score, 0, 100)) / 100.0

    size = cfg.bankroll_sol * cfg.kelly_fraction * kelly_f * conviction_mult * risk_mult

    # caps
    size = min(size, cfg.max_ticket_sol)
    remaining = max(0.0, cfg.max_token_exposure_sol - current_token_exposure_sol)
    size = min(size, remaining)
    if token_liquidity_sol > 0:
        size = min(size, cfg.liquidity_fraction_cap * token_liquidity_sol)

    return float(size) if size >= cfg.min_ticket_sol else 0.0
