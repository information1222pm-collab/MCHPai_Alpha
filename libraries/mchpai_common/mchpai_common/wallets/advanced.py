"""Advanced wallet profiling.

Extends the six baseline axes (in :mod:`profiling`) with the deeper metrics the
Phase-1 spec calls for, grouped as:

  performance  — roi, sharpe, win_rate, kelly_fraction, expectancy
  timing       — entry_percentile, exit_percentile, avg_hold_seconds
  conviction   — avg_size, scaling_behavior, diamond_hand_score
  intelligence — rug_avoidance, smart_entry_score, mean_reversion_tendency

Everything is computed from realized round-trips plus optional lookups, so it is
pure and unit-testable. The composite ``wallet_alpha_score`` is the canonical
0..100 quality score for a wallet.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from ..schemas.common import Side
from ..schemas.trade import Trade
from .profiling import match_round_trips

# (low, high) realized price range over a token's life, for percentile context
PriceRangeLookup = Callable[[str], tuple[float, float] | None]


@dataclass
class AdvancedWalletProfile:
    address: str
    closed_trades: int = 0

    # performance
    roi: float = 0.0
    sharpe: float = 0.0
    win_rate: float = 0.0
    kelly_fraction: float = 0.0
    expectancy_sol: float = 0.0

    # timing
    entry_percentile: float = 0.5      # 0 = bought the bottom, 1 = bought the top
    exit_percentile: float = 0.5       # 1 = sold the top
    avg_hold_seconds: float = 0.0

    # conviction
    avg_size_sol: float = 0.0
    scaling_behavior: float = 0.0      # tendency to add to winners (-1..1)
    diamond_hand_score: float = 0.0    # 0..1 patience through holds

    # intelligence
    rug_avoidance: float = 1.0         # 1 - share of rugged tokens touched
    smart_entry_score: float = 0.5     # 1 - entry_percentile (buying low)
    mean_reversion_tendency: float = 0.5

    wallet_alpha_score: float = 0.0
    components: dict[str, float] = field(default_factory=dict)


def _kelly(win_rate: float, avg_win: float, avg_loss: float) -> float:
    if avg_loss <= 0:
        return 0.0
    r = avg_win / avg_loss
    f = win_rate - (1 - win_rate) / r if r > 0 else 0.0
    return float(np.clip(f, 0.0, 1.0))


def profile_wallet_advanced(
    address: str,
    trades: list[Trade],
    *,
    rug_mints: set[str] | None = None,
    price_range: PriceRangeLookup | None = None,
) -> AdvancedWalletProfile:
    rug_mints = rug_mints or set()
    rts = match_round_trips(trades)
    if not rts:
        return AdvancedWalletProfile(address=address)

    rets = np.array([rt.ret for rt in rts], dtype=float)
    pnls = np.array([rt.pnl_sol for rt in rts], dtype=float)
    costs = np.array([rt.cost_sol for rt in rts], dtype=float)
    holds = np.array([rt.hold_seconds for rt in rts], dtype=float)

    wins = pnls[pnls > 0]
    losses = -pnls[pnls < 0]
    win_rate = float((pnls > 0).mean())
    avg_win = float(wins.mean()) if wins.size else 0.0
    avg_loss = float(losses.mean()) if losses.size else 0.0

    roi = float(pnls.sum() / costs.sum()) if costs.sum() > 0 else 0.0
    sharpe = float(rets.mean() / rets.std(ddof=0)) if rets.std(ddof=0) > 1e-9 else 0.0
    expectancy = float(pnls.mean())
    kelly = _kelly(win_rate, avg_win, avg_loss)

    # timing percentiles from per-token price range, if available
    entry_pcts, exit_pcts = [], []
    if price_range is not None:
        buys = [t for t in trades if t.side == Side.buy and t.price_sol]
        sells = [t for t in trades if t.side == Side.sell and t.price_sol]
        for t in buys:
            rng = price_range(t.mint)
            if rng and rng[1] > rng[0]:
                entry_pcts.append((t.price_sol - rng[0]) / (rng[1] - rng[0]))
        for t in sells:
            rng = price_range(t.mint)
            if rng and rng[1] > rng[0]:
                exit_pcts.append((t.price_sol - rng[0]) / (rng[1] - rng[0]))
    entry_pct = float(np.clip(np.mean(entry_pcts), 0, 1)) if entry_pcts else 0.5
    exit_pct = float(np.clip(np.mean(exit_pcts), 0, 1)) if exit_pcts else 0.5

    # conviction: scaling = do they buy more after a profitable run?
    buy_sizes = [t.sol_amount for t in trades if t.side == Side.buy]
    scaling = 0.0
    if len(buy_sizes) >= 2:
        diffs = np.diff(buy_sizes)
        scaling = float(np.clip(np.tanh(np.mean(np.sign(diffs))), -1, 1))
    diamond = float(np.clip(np.median(holds) / 3600.0, 0, 1))  # 1h median hold → 1

    # intelligence
    touched = {t.mint for t in trades}
    rug_avoidance = 1.0 - (len(touched & rug_mints) / len(touched)) if touched else 1.0
    smart_entry = 1.0 - entry_pct
    mean_reversion = float(np.clip(1.0 - entry_pct, 0, 1))  # buying low ⇒ mean-revert

    components = {
        "roi": float(np.clip(roi / 5.0, 0, 1)),
        "sharpe": float(np.clip(sharpe / 3.0, 0, 1)),
        "win_rate": win_rate,
        "kelly": kelly,
        "smart_entry": smart_entry,
        "rug_avoidance": float(rug_avoidance),
        "diamond": diamond,
    }
    weights = {
        "roi": 0.22, "sharpe": 0.18, "win_rate": 0.15, "kelly": 0.10,
        "smart_entry": 0.13, "rug_avoidance": 0.15, "diamond": 0.07,
    }
    confidence = len(rts) / (len(rts) + 10)
    alpha = 100.0 * sum(components[k] * weights[k] for k in weights) * (0.5 + 0.5 * confidence)

    return AdvancedWalletProfile(
        address=address,
        closed_trades=len(rts),
        roi=roi,
        sharpe=sharpe,
        win_rate=win_rate,
        kelly_fraction=kelly,
        expectancy_sol=expectancy,
        entry_percentile=entry_pct,
        exit_percentile=exit_pct,
        avg_hold_seconds=float(holds.mean()),
        avg_size_sol=float(costs.mean()),
        scaling_behavior=scaling,
        diamond_hand_score=diamond,
        rug_avoidance=float(rug_avoidance),
        smart_entry_score=smart_entry,
        mean_reversion_tendency=mean_reversion,
        wallet_alpha_score=float(np.clip(alpha, 0, 100)),
        components=components,
    )
