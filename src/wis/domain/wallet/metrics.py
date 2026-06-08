"""Wallet metrics — statistics over observed behavior.

These dataclasses turn a wallet's :class:`ClosedTrade` history into the
quantitative vocabulary of the charter: performance, timing, conviction, risk
and intelligence. Two principles govern every field here:

1. **Reality over prediction.** A metric is computed only from facts. Where a
   metric genuinely requires data we have not yet ingested (token labels for
   rug exposure, full price paths for trend-following tendency), the field is
   ``None`` — "not yet observable" — rather than a fabricated number. Honest
   absence beats confident fiction.
2. **Point-in-time correctness.** Timing metrics consult :class:`PriceContext`,
   which only exposes prices known at the moment of each trade.

Social/graph metrics (influence, centrality, cluster participation) are *not*
computed here — they are properties of ``graph(t)``, not of a wallet in
isolation, and live in :mod:`wis.domain.graph`.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from wis.domain import stats
from wis.domain.time import DAY, WEEK, Nanos
from wis.domain.wallet.price_context import PriceContext
from wis.domain.wallet.trade_ledger import ClosedTrade, OpenPosition

ROI_30D = 30 * DAY


@dataclass(frozen=True, slots=True)
class MetricInputs:
    """Everything the metric computations are allowed to see."""

    closed: list[ClosedTrade]
    positions: list[OpenPosition]
    reference_time: Nanos  # the "now" against which windows are measured
    buy_count: int
    sell_count: int
    price_context: PriceContext | None = None


def _returns(closed: list[ClosedTrade]) -> list[float]:
    out = []
    for t in closed:
        r = t.trade_return
        if r is not None:
            out.append(float(r))
    return out


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    lifetime_roi: float | None
    roi_30d: float | None
    roi_7d: float | None
    average_multiple: float | None
    median_multiple: float | None
    sharpe_ratio: float | None
    sortino_ratio: float | None
    expectancy: float | None
    profit_factor: float | None
    kelly_fraction: float | None
    capital_efficiency: float | None
    win_rate: float | None
    max_drawdown: float
    recovery_factor: float | None

    @staticmethod
    def compute(mi: MetricInputs) -> PerformanceMetrics:
        closed = mi.closed
        if not closed:
            return PerformanceMetrics(
                None, None, None, None, None, None, None, None, None, None, None, None, 0.0, None
            )

        total_cost = sum((t.cost for t in closed), Fraction(0))
        total_pnl = sum((t.pnl for t in closed), Fraction(0))
        lifetime_roi = float(total_pnl / total_cost) if total_cost > 0 else None

        def windowed_roi(window: int) -> float | None:
            lo = mi.reference_time - window
            sel = [t for t in closed if t.exit_time >= lo]
            c = sum((t.cost for t in sel), Fraction(0))
            p = sum((t.pnl for t in sel), Fraction(0))
            return float(p / c) if c > 0 else None

        multiples = [float(t.multiple) for t in closed if t.multiple is not None]
        rets = _returns(closed)
        pnls = [float(t.pnl) for t in closed]

        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        win_rate = len(wins) / len(pnls) if pnls else None
        gross_loss = -sum(losses)
        profit_factor = (sum(wins) / gross_loss) if gross_loss > 0 else None

        # Kelly fraction f* = W - (1 - W) / R, with R the win/loss payoff ratio.
        kelly = None
        if win_rate is not None and wins and losses:
            avg_win = stats.mean(wins)
            avg_loss = -stats.mean(losses)
            if avg_loss > 0:
                R = avg_win / avg_loss
                kelly = win_rate - (1 - win_rate) / R

        sd = stats.pstdev(rets)
        sharpe = stats.mean(rets) / sd if sd > 0 else None
        dd_dev = stats.downside_deviation(rets)
        sortino = stats.mean(rets) / dd_dev if dd_dev > 0 else None

        # Equity curve = cumulative realised pnl in exit order.
        ordered = sorted(closed, key=lambda t: (t.exit_time, t.exit_sequence))
        equity, running = [], 0.0
        for t in ordered:
            running += float(t.pnl)
            equity.append(running)
        mdd = stats.max_drawdown(equity)
        recovery = (float(total_pnl) / mdd) if mdd > 0 else None
        capital_eff = float(total_pnl) / stats.mean([float(t.cost) for t in closed]) if closed else None

        return PerformanceMetrics(
            lifetime_roi=lifetime_roi,
            roi_30d=windowed_roi(ROI_30D),
            roi_7d=windowed_roi(WEEK),
            average_multiple=stats.mean(multiples) if multiples else None,
            median_multiple=stats.median(multiples) if multiples else None,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            expectancy=stats.mean(pnls) if pnls else None,
            profit_factor=profit_factor,
            kelly_fraction=kelly,
            capital_efficiency=capital_eff,
            win_rate=win_rate,
            max_drawdown=mdd,
            recovery_factor=recovery,
        )


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TimingMetrics:
    average_hold_seconds: float | None
    median_hold_seconds: float | None
    patience_score: float | None
    reaction_speed_seconds: float | None  # avg gap between token genesis and entry
    entry_percentile: float | None  # mean rank of entry price (lower = cheaper)
    exit_percentile: float | None  # mean rank of exit price (higher = richer)

    @staticmethod
    def compute(mi: MetricInputs) -> TimingMetrics:
        closed = mi.closed
        if not closed:
            return TimingMetrics(None, None, None, None, None, None)

        holds = [t.hold_nanos / 1e9 for t in closed]
        median_hold = stats.median(holds)
        # Patience: saturating map of median hold to (0,1) with a 1-day anchor.
        patience = median_hold / (median_hold + DAY / 1e9) if median_hold > 0 else 0.0

        pc = mi.price_context
        reaction = entry_pct = exit_pct = None
        if pc is not None:
            reactions, entries, exits = [], [], []
            for t in closed:
                genesis = pc.genesis(t.token)
                if genesis is not None:
                    reactions.append((int(t.entry_time) - int(genesis)) / 1e9)
                entry_price = float(t.cost / t.qty) if t.qty > 0 else None
                exit_price = float(t.proceeds / t.qty) if t.qty > 0 else None
                if entry_price is not None:
                    r = stats.percentile_rank(entry_price, pc.prices_up_to(t.token, t.entry_time))
                    if r is not None:
                        entries.append(r)
                if exit_price is not None:
                    r = stats.percentile_rank(exit_price, pc.prices_up_to(t.token, t.exit_time))
                    if r is not None:
                        exits.append(r)
            reaction = stats.mean(reactions) if reactions else None
            entry_pct = stats.mean(entries) if entries else None
            exit_pct = stats.mean(exits) if exits else None

        return TimingMetrics(
            average_hold_seconds=stats.mean(holds),
            median_hold_seconds=median_hold,
            patience_score=patience,
            reaction_speed_seconds=reaction,
            entry_percentile=entry_pct,
            exit_percentile=exit_pct,
        )


# ---------------------------------------------------------------------------
# Conviction
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConvictionMetrics:
    average_position_size: float | None  # quote units per trade
    position_concentration: float  # Herfindahl over per-token cost (0..1)
    portfolio_diversity: float  # 1 - concentration (0..1)
    distinct_tokens: int
    scaling_behavior: float | None  # avg buys per token: >1 means averaging in
    diamond_hands_score: float | None  # proxy: holding through time

    @staticmethod
    def compute(mi: MetricInputs) -> ConvictionMetrics:
        closed = mi.closed
        by_token_cost: dict[str, float] = {}
        for t in closed:
            by_token_cost[t.token.value] = by_token_cost.get(t.token.value, 0.0) + float(t.cost)
        for p in mi.positions:
            by_token_cost[p.token.value] = by_token_cost.get(p.token.value, 0.0) + float(p.cost)

        concentration = stats.herfindahl(list(by_token_cost.values()))
        distinct = len(by_token_cost)
        avg_size = stats.mean([float(t.cost) for t in closed]) if closed else None
        scaling = (mi.buy_count / distinct) if distinct > 0 else None

        diamond = None
        if closed:
            # Saturating credit for holding: 1 day of hold ~ full credit per trade.
            diamond = stats.mean([min(t.hold_nanos / DAY, 1.0) for t in closed])

        return ConvictionMetrics(
            average_position_size=avg_size,
            position_concentration=concentration,
            portfolio_diversity=1.0 - concentration,
            distinct_tokens=distinct,
            scaling_behavior=scaling,
            diamond_hands_score=diamond,
        )


# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RiskMetrics:
    loss_frequency: float | None
    max_consecutive_losses: int
    volatility_tolerance: float | None  # stdev of trade returns
    tail_risk_cvar5: float | None  # mean of worst 5% returns (negative = bad)
    rug_exposure: float | None  # requires token risk labels — pending enrichment
    scam_exposure: float | None  # requires token risk labels — pending enrichment

    @staticmethod
    def compute(mi: MetricInputs) -> RiskMetrics:
        closed = mi.closed
        if not closed:
            return RiskMetrics(None, 0, None, None, None, None)

        ordered = sorted(closed, key=lambda t: (t.exit_time, t.exit_sequence))
        loss_flags = [t.pnl < 0 for t in ordered]
        loss_freq = sum(loss_flags) / len(loss_flags)
        rets = sorted(_returns(closed))
        vol = stats.pstdev(rets) if rets else None
        cvar = None
        if rets:
            k = max(1, len(rets) // 20)  # worst 5%
            cvar = stats.mean(rets[:k])

        return RiskMetrics(
            loss_frequency=loss_freq,
            max_consecutive_losses=stats.max_consecutive(loss_flags),
            volatility_tolerance=vol,
            tail_risk_cvar5=cvar,
            # Honest absence: these need a token risk-label feed we have not
            # ingested in the core. Surfaced as pending, never faked.
            rug_exposure=None,
            scam_exposure=None,
        )
