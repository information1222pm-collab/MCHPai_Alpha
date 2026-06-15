"""FIFO round-trip matching and behavioral profiling.

A wallet's edge is only visible in *closed* positions. We match each sell against
the oldest open buys (FIFO) for the same mint to form round-trips, then derive:

    roi, win_rate, avg_hold_seconds, conviction, risk, profit_consistency

These feed ``wallet_alpha_score`` (see services/prediction-engine and
models/). Small-sample wallets are shrunk toward priors at scoring time, not
here — this module reports raw, honest statistics.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field

import numpy as np

from ..schemas.common import Side
from ..schemas.trade import Trade
from ..schemas.wallet import WalletProfile


@dataclass
class _Lot:
    token_amount: float
    sol_cost: float
    ts: float          # epoch seconds


@dataclass
class RoundTrip:
    mint: str
    token_amount: float
    cost_sol: float
    proceeds_sol: float
    hold_seconds: float

    @property
    def pnl_sol(self) -> float:
        return self.proceeds_sol - self.cost_sol

    @property
    def ret(self) -> float:
        return self.pnl_sol / self.cost_sol if self.cost_sol > 0 else 0.0


def _ts(trade: Trade) -> float:
    return trade.block_time.timestamp() if trade.block_time else 0.0


def match_round_trips(trades: list[Trade]) -> list[RoundTrip]:
    """FIFO-match sells against buys per mint to produce closed round-trips."""
    open_lots: dict[str, deque[_Lot]] = defaultdict(deque)
    round_trips: list[RoundTrip] = []

    for t in sorted(trades, key=_ts):
        if t.token_amount <= 0:
            continue
        if t.side == Side.buy:
            open_lots[t.mint].append(
                _Lot(token_amount=t.token_amount, sol_cost=t.sol_amount, ts=_ts(t))
            )
        else:  # sell — consume oldest lots
            remaining = t.token_amount
            sell_px = t.sol_amount / t.token_amount if t.token_amount else 0.0
            lots = open_lots[t.mint]
            while remaining > 1e-12 and lots:
                lot = lots[0]
                take = min(remaining, lot.token_amount)
                frac = take / lot.token_amount if lot.token_amount else 0.0
                cost = lot.sol_cost * frac
                proceeds = sell_px * take
                round_trips.append(
                    RoundTrip(
                        mint=t.mint,
                        token_amount=take,
                        cost_sol=cost,
                        proceeds_sol=proceeds,
                        hold_seconds=max(0.0, _ts(t) - lot.ts),
                    )
                )
                lot.token_amount -= take
                lot.sol_cost -= cost
                remaining -= take
                if lot.token_amount <= 1e-12:
                    lots.popleft()
    return round_trips


def profile_wallet(
    address: str, trades: list[Trade], *, window_days: int = 30, bankroll_hint: float | None = None
) -> WalletProfile:
    """Compute the six behavioral axes for ``address`` from its trades."""
    rts = match_round_trips(trades)
    if not rts:
        return WalletProfile(address=address, window_days=window_days, closed_trades=0)

    rets = np.array([rt.ret for rt in rts], dtype=float)
    pnls = np.array([rt.pnl_sol for rt in rts], dtype=float)
    costs = np.array([rt.cost_sol for rt in rts], dtype=float)
    holds = np.array([rt.hold_seconds for rt in rts], dtype=float)

    total_cost = float(costs.sum())
    roi = float(pnls.sum() / total_cost) if total_cost > 0 else 0.0
    win_rate = float((pnls > 0).mean())
    avg_hold = float(holds.mean())

    # conviction: typical position size relative to a bankroll proxy, with a
    # bonus for averaging-in (multiple buys before a sell ⇒ higher conviction).
    bankroll = bankroll_hint or max(float(costs.max()), 1e-9)
    conviction = float(np.clip(costs.mean() / bankroll, 0.0, 1.0))

    # risk: dispersion of returns (volatility), clipped to 0..1.
    risk = float(np.clip(rets.std(ddof=0), 0.0, 1.0))

    # profit_consistency: 1 - coefficient of variation of returns (clamped).
    mean_abs = float(np.mean(np.abs(rets)))
    cv = float(rets.std(ddof=0) / mean_abs) if mean_abs > 1e-9 else 1.0
    profit_consistency = float(np.clip(1.0 - cv, 0.0, 1.0))

    return WalletProfile(
        address=address,
        window_days=window_days,
        closed_trades=len(rts),
        roi=roi,
        win_rate=win_rate,
        avg_hold_seconds=avg_hold,
        conviction=conviction,
        risk=risk,
        profit_consistency=profit_consistency,
        realized_pnl_sol=float(pnls.sum()),
    )
