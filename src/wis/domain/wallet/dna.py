"""Wallet DNA — the qualitative profile distilled from quantitative behavior.

DNA answers the question the charter cares about: *what kind of participant is
this, really?* It names a wallet's strengths and weaknesses, its behavioral
tendencies, its risk appetite and capital style — and, crucially, it is itself
time-indexed, because a wallet's DNA *mutates*. A patient accumulator can decay
into a reflexive degen; a reckless gambler can mature. We capture the genome at
``t`` so its evolution becomes observable.

DNA is *derived*, never asserted: every trait is backed by a metric and a
threshold, so a profile is explainable down to the trade.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from wis.domain.wallet.metrics import (
    ConvictionMetrics,
    PerformanceMetrics,
    RiskMetrics,
    TimingMetrics,
)


class Trait(StrEnum):
    # Capital / conviction
    HIGH_CONVICTION = "high_conviction"
    DIVERSIFIED = "diversified"
    CONCENTRATED = "concentrated"
    SCALES_IN = "scales_in"
    # Timing
    PATIENT = "patient"
    FAST_REACTOR = "fast_reactor"
    EARLY_ENTRY = "early_entry"
    GOOD_EXITS = "good_exits"
    # Risk
    RISK_TOLERANT = "risk_tolerant"
    RISK_AVERSE = "risk_averse"
    LOSS_PRONE = "loss_prone"
    # Performance
    PROFITABLE = "profitable"
    HIGH_EXPECTANCY = "high_expectancy"
    CONSISTENT = "consistent"
    DRAWDOWN_HEAVY = "drawdown_heavy"


@dataclass(frozen=True, slots=True)
class WalletDNA:
    strengths: tuple[Trait, ...] = ()
    weaknesses: tuple[Trait, ...] = ()
    tendencies: tuple[Trait, ...] = ()
    # Free-form, explainable annotations: trait -> the evidence that earned it.
    evidence: dict[str, str] = field(default_factory=dict)

    def summary(self) -> str:
        s = ", ".join(t.value for t in self.strengths) or "none observed yet"
        w = ", ".join(t.value for t in self.weaknesses) or "none observed yet"
        return f"strengths: {s} | weaknesses: {w}"

    @staticmethod
    def sequence(
        perf: PerformanceMetrics,
        timing: TimingMetrics,
        conviction: ConvictionMetrics,
        risk: RiskMetrics,
    ) -> WalletDNA:
        """Express the genome from the current metric groups. Pure and
        threshold-driven so it is reproducible and auditable."""
        strengths: list[Trait] = []
        weaknesses: list[Trait] = []
        tendencies: list[Trait] = []
        evidence: dict[str, str] = {}

        def mark(bucket: list[Trait], trait: Trait, why: str) -> None:
            bucket.append(trait)
            evidence[trait.value] = why

        # Performance
        if perf.lifetime_roi is not None and perf.lifetime_roi > 0:
            mark(strengths, Trait.PROFITABLE, f"lifetime ROI {perf.lifetime_roi:.2%}")
        if perf.expectancy is not None and perf.expectancy > 0:
            mark(strengths, Trait.HIGH_EXPECTANCY, f"expectancy {perf.expectancy:.4g}/trade")
        if perf.sharpe_ratio is not None and perf.sharpe_ratio > 1.0:
            mark(strengths, Trait.CONSISTENT, f"per-trade Sharpe {perf.sharpe_ratio:.2f}")
        if perf.recovery_factor is not None and perf.recovery_factor < 1.0:
            mark(weaknesses, Trait.DRAWDOWN_HEAVY, f"recovery factor {perf.recovery_factor:.2f}")

        # Conviction
        if conviction.position_concentration > 0.5:
            mark(tendencies, Trait.CONCENTRATED, f"HHI {conviction.position_concentration:.2f}")
        elif conviction.portfolio_diversity > 0.8:
            mark(tendencies, Trait.DIVERSIFIED, f"diversity {conviction.portfolio_diversity:.2f}")
        if conviction.diamond_hands_score is not None and conviction.diamond_hands_score > 0.6:
            mark(strengths, Trait.HIGH_CONVICTION, f"diamond-hands {conviction.diamond_hands_score:.2f}")
        if conviction.scaling_behavior is not None and conviction.scaling_behavior > 1.5:
            mark(tendencies, Trait.SCALES_IN, f"{conviction.scaling_behavior:.1f} buys/token")

        # Timing
        if timing.patience_score is not None and timing.patience_score > 0.6:
            mark(tendencies, Trait.PATIENT, f"patience {timing.patience_score:.2f}")
        elif timing.patience_score is not None and timing.patience_score < 0.2:
            mark(tendencies, Trait.FAST_REACTOR, f"patience {timing.patience_score:.2f}")
        if timing.entry_percentile is not None and timing.entry_percentile < 0.3:
            mark(strengths, Trait.EARLY_ENTRY, f"entry percentile {timing.entry_percentile:.2f}")
        if timing.exit_percentile is not None and timing.exit_percentile > 0.7:
            mark(strengths, Trait.GOOD_EXITS, f"exit percentile {timing.exit_percentile:.2f}")

        # Risk
        if risk.volatility_tolerance is not None and risk.volatility_tolerance > 1.0:
            mark(tendencies, Trait.RISK_TOLERANT, f"return vol {risk.volatility_tolerance:.2f}")
        elif risk.volatility_tolerance is not None and risk.volatility_tolerance < 0.25:
            mark(tendencies, Trait.RISK_AVERSE, f"return vol {risk.volatility_tolerance:.2f}")
        if risk.loss_frequency is not None and risk.loss_frequency > 0.6:
            mark(weaknesses, Trait.LOSS_PRONE, f"loss frequency {risk.loss_frequency:.2%}")

        return WalletDNA(
            strengths=tuple(strengths),
            weaknesses=tuple(weaknesses),
            tendencies=tuple(tendencies),
            evidence=evidence,
        )
