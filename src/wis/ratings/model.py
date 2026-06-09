"""The wallet rating — a compressed, honest summary of observed behavior.

Quote-internal ratios (win rate, trade multiples, Sharpe) are pooled across quote
assets because a ratio is unitless. Absolute money (PnL, ROI%) is kept **per
quote** — ``pnl_by_quote`` / ``roi_by_quote`` — because summing SOL and USDC is
meaningless. Every rating carries ``closed_trades`` (its denominator) and
``confidence``: a rating without them is a half-truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class WalletRating:
    wallet: str
    closed_trades: int       # the denominator behind every rate
    distinct_tokens: int
    open_positions: int
    confidence: float        # 0..1, grows with observation (Statistics doctrine)

    # Quote-internal (poolable) — valid across mixed quote assets:
    win_rate: float | None
    median_multiple: float | None
    average_multiple: float | None
    sharpe: float | None

    # Truth-weighted scores (already confidence-shrunk):
    alpha_score: float | None
    expected_value_score: float | None
    conviction_score: float | None
    risk_score: float | None
    timing_score: float | None

    # Absolute money — PER QUOTE, never summed across currencies:
    primary_quote: str | None
    pnl_by_quote: dict[str, float] = field(default_factory=dict)   # realized pnl
    roi_by_quote: dict[str, float] = field(default_factory=dict)   # pnl/cost (pnl %)

    @property
    def primary_pnl(self) -> float | None:
        return self.pnl_by_quote.get(self.primary_quote) if self.primary_quote else None

    @property
    def primary_roi(self) -> float | None:
        return self.roi_by_quote.get(self.primary_quote) if self.primary_quote else None
