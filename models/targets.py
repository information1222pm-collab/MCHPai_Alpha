"""Supervised targets derived from ground truth.

The Phase-1 doctrine: data quality first. These four targets are simple,
high-signal functions of the *frozen* ground-truth labels, so models can't leak
the future. Start here (XGBoost) before any sequence model.

    rug_probability       P(token rugs)
    survival_probability  P(token survives / goes viral, i.e. not a rug)
    tenx_probability      P(token does >=10x within 24h)
    buy_probability       P(a profitable entry: >=2x within 6h, not an early rug)
"""

from __future__ import annotations

from collections.abc import Callable

from mchpai_common.schemas.ground_truth import GroundTruth, Outcome

# name -> (label_fn, is_classification)
Target = Callable[[GroundTruth], float]


def rug_probability(gt: GroundTruth) -> float:
    return 1.0 if gt.outcome == Outcome.rugged else 0.0


def survival_probability(gt: GroundTruth) -> float:
    return 1.0 if gt.outcome in (Outcome.survived, Outcome.viral) else 0.0


def tenx_probability(gt: GroundTruth) -> float:
    return 1.0 if gt.label(10, "24h") else 0.0


def buy_probability(gt: GroundTruth) -> float:
    # a "good buy" = doubled within 6h and did not rug inside the first hour
    early_rug = gt.outcome == Outcome.rugged and (gt.survival_seconds or 1e9) <= 3600
    return 1.0 if (gt.label(2, "6h") and not early_rug) else 0.0


TARGETS: dict[str, Target] = {
    "rug_probability": rug_probability,
    "survival_probability": survival_probability,
    "tenx_probability": tenx_probability,
    "buy_probability": buy_probability,
}


def label_for(target: str, gt: GroundTruth) -> float:
    return TARGETS[target](gt)
