"""Creator profiling & scoring.

Aggregates per-launch outcomes into a creator's track record:

    launch_count · rug_count/rug_rate · best_multiple · median_multiple ·
    holder_retention · median_survival · volume_generated · repeat_buyer_rate

``creator_score`` (0..100) rewards survival, multiples, retention, repeat buyers
and an established track record, while heavily penalizing a high rug rate. New
creators are shrunk toward a neutral prior (small-sample guard).
"""

from __future__ import annotations

import statistics as stats
from dataclasses import dataclass, field

import numpy as np


@dataclass
class TokenLaunch:
    """One past launch's realized outcome (from ground truth)."""

    mint: str
    rugged: bool
    max_multiple: float = 1.0           # peak / reference
    survival_seconds: float = 0.0
    holder_retention: float = 0.0       # holders_now / holders_peak (0..1)
    volume_sol: float = 0.0
    repeat_buyers: int = 0
    total_buyers: int = 0


@dataclass
class CreatorProfile:
    creator: str
    launch_count: int = 0
    rug_count: int = 0
    rug_rate: float = 0.0
    best_multiple: float = 1.0
    median_multiple: float = 1.0
    median_survival_seconds: float = 0.0
    avg_holder_retention: float = 0.0
    volume_generated_sol: float = 0.0
    repeat_buyer_rate: float = 0.0
    creator_score: float = 0.0
    components: dict[str, float] = field(default_factory=dict)


# Bayesian shrinkage for thin-history creators.
_PRIOR_RUG_RATE = 0.5
_PRIOR_STRENGTH = 3


def build_creator_profile(creator: str, launches: list[TokenLaunch]) -> CreatorProfile:
    n = len(launches)
    if n == 0:
        return CreatorProfile(creator=creator)

    rugs = sum(1 for l in launches if l.rugged)
    multiples = [max(1.0, l.max_multiple) for l in launches]
    survivals = [l.survival_seconds for l in launches]
    retentions = [l.holder_retention for l in launches]
    vol = sum(l.volume_sol for l in launches)
    total_buyers = sum(l.total_buyers for l in launches)
    repeat_buyers = sum(l.repeat_buyers for l in launches)

    rug_rate = (rugs + _PRIOR_RUG_RATE * _PRIOR_STRENGTH) / (n + _PRIOR_STRENGTH)
    repeat_rate = repeat_buyers / total_buyers if total_buyers > 0 else 0.0

    profile = CreatorProfile(
        creator=creator,
        launch_count=n,
        rug_count=rugs,
        rug_rate=rug_rate,
        best_multiple=max(multiples),
        median_multiple=float(stats.median(multiples)),
        median_survival_seconds=float(stats.median(survivals)) if survivals else 0.0,
        avg_holder_retention=float(np.mean(retentions)) if retentions else 0.0,
        volume_generated_sol=vol,
        repeat_buyer_rate=repeat_rate,
    )
    profile.creator_score, profile.components = creator_score(profile)
    return profile


def creator_score(p: CreatorProfile) -> tuple[float, dict[str, float]]:
    # each component in 0..1
    comp = {
        "anti_rug": float(np.clip(1.0 - p.rug_rate, 0, 1)),
        "best_multiple": float(np.clip(np.log10(max(p.best_multiple, 1.0)) / 2.0, 0, 1)),  # 100x→1
        "median_multiple": float(np.clip((p.median_multiple - 1.0) / 4.0, 0, 1)),          # 5x→1
        "survival": float(np.clip(p.median_survival_seconds / 604800.0, 0, 1)),            # 7d→1
        "retention": float(np.clip(p.avg_holder_retention, 0, 1)),
        "repeat_buyers": float(np.clip(p.repeat_buyer_rate, 0, 1)),
    }
    weights = {
        "anti_rug": 0.35, "best_multiple": 0.15, "median_multiple": 0.15,
        "survival": 0.15, "retention": 0.12, "repeat_buyers": 0.08,
    }
    raw = sum(comp[k] * weights[k] for k in weights)
    confidence = p.launch_count / (p.launch_count + _PRIOR_STRENGTH)
    score = 100.0 * raw * (0.4 + 0.6 * confidence)
    return float(np.clip(score, 0, 100)), comp
