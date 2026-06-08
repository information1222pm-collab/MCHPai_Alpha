"""Wallet scores — compressed, comparable expressions of behavioral quality.

The charter is explicit: *do not optimize scores for profitability; optimize for
truth.* Accordingly every score here is a transparent, monotone function of
observed metrics, shrunk toward neutral by the confidence the sample supports.
There is no fitted model, no label of "good trader" to chase — only a faithful
compression of what the wallet has demonstrably done.

Graph-dependent scores (influence, cluster) are ``None`` until ``graph(t)`` is
supplied, rather than guessed.
"""

from __future__ import annotations

from dataclasses import dataclass

from wis.domain.graph.metrics import GraphWalletMetrics
from wis.domain.wallet.state import WalletFrame
from wis.scoring import normalize as nz


@dataclass(frozen=True, slots=True)
class WalletScores:
    timing_score: float | None
    conviction_score: float | None
    risk_score: float | None
    consistency_score: float | None
    expected_value_score: float | None
    influence_score: float | None
    cluster_score: float | None
    wallet_alpha_score: float | None
    # How much observation backs these numbers (0..1). Surfaced, not hidden,
    # because a score without its confidence is a half-truth.
    confidence: float


def score_wallet(frame: WalletFrame, graph: GraphWalletMetrics | None = None) -> WalletScores:
    p = frame.performance
    t = frame.timing
    c = frame.conviction
    r = frame.risk
    n = _sample_size(frame)
    conf = nz.confidence(n)

    timing = _timing_score(t)
    conviction = _conviction_score(c)
    risk = _risk_score(p, r)
    consistency = _consistency_score(p, r)
    ev = _expected_value_score(p)

    influence = cluster = None
    if graph is not None:
        influence = nz.clamp01(graph.influence_score)
        cluster = nz.clamp01(graph.cluster_score)

    # Alpha is the truth-weighted blend of the components we can observe. Weights
    # favour evidence of skill (EV, consistency, timing) over mere activity.
    components: list[tuple[float, float | None]] = [
        (0.30, ev),
        (0.25, consistency),
        (0.20, timing),
        (0.15, risk),
        (0.10, conviction),
    ]
    alpha = _weighted(components)

    # Shrink every score toward neutral by confidence: thin samples cannot shout.
    return WalletScores(
        timing_score=nz.shrink(timing, conf) if timing is not None else None,
        conviction_score=nz.shrink(conviction, conf) if conviction is not None else None,
        risk_score=nz.shrink(risk, conf) if risk is not None else None,
        consistency_score=nz.shrink(consistency, conf) if consistency is not None else None,
        expected_value_score=nz.shrink(ev, conf) if ev is not None else None,
        influence_score=influence,
        cluster_score=cluster,
        wallet_alpha_score=nz.shrink(alpha, conf) if alpha is not None else None,
        confidence=conf,
    )


def _sample_size(frame: WalletFrame) -> int:
    # Closed trades are the evidence unit; confidence grows with them.
    return frame.sample_size


def _timing_score(t) -> float | None:
    parts: list[float | None] = []
    if t.entry_percentile is not None:
        parts.append(1.0 - t.entry_percentile)  # cheaper entry = better
    if t.exit_percentile is not None:
        parts.append(t.exit_percentile)  # richer exit = better
    if t.patience_score is not None:
        parts.append(t.patience_score)
    return nz.mean_of_present(parts)


def _conviction_score(c) -> float | None:
    parts: list[float | None] = []
    if c.diamond_hands_score is not None:
        parts.append(c.diamond_hands_score)
    if c.scaling_behavior is not None:
        parts.append(nz.logistic(c.scaling_behavior, midpoint=1.0, scale=0.5))
    # Concentration as conviction: belief shows as willingness to concentrate,
    # but only mildly weighted — concentration is also risk.
    parts.append(c.position_concentration)
    return nz.mean_of_present(parts)


def _risk_score(p, r) -> float | None:
    # Higher = better-managed risk.
    parts: list[float | None] = []
    if r.loss_frequency is not None:
        parts.append(1.0 - r.loss_frequency)
    if p.recovery_factor is not None:
        parts.append(nz.logistic(p.recovery_factor, midpoint=1.0, scale=1.0))
    if r.tail_risk_cvar5 is not None:
        # cvar is a (usually negative) return; closer to 0 = safer tail.
        parts.append(nz.logistic(r.tail_risk_cvar5, midpoint=-0.5, scale=0.5))
    return nz.mean_of_present(parts)


def _consistency_score(p, r) -> float | None:
    parts: list[float | None] = []
    if p.sharpe_ratio is not None:
        parts.append(nz.logistic(p.sharpe_ratio, midpoint=0.0, scale=1.0))
    if p.win_rate is not None:
        parts.append(p.win_rate)
    if r.volatility_tolerance is not None:
        # Lower return volatility = more consistent.
        parts.append(1.0 - nz.logistic(r.volatility_tolerance, midpoint=1.0, scale=1.0))
    return nz.mean_of_present(parts)


def _expected_value_score(p) -> float | None:
    parts: list[float | None] = []
    if p.expectancy is not None:
        parts.append(nz.logistic(p.expectancy, midpoint=0.0, scale=1.0))
    if p.profit_factor is not None:
        parts.append(nz.logistic(p.profit_factor, midpoint=1.0, scale=1.0))
    if p.kelly_fraction is not None:
        parts.append(nz.clamp01(p.kelly_fraction))
    return nz.mean_of_present(parts)


def _weighted(components: list[tuple[float, float | None]]) -> float | None:
    num = 0.0
    den = 0.0
    for w, v in components:
        if v is not None:
            num += w * v
            den += w
    return num / den if den > 0 else None
