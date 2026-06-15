"""Incremental wallet state reducer — the wallet 'movie'.

Maintains live FIFO lots per mint so that, after every swap, we can emit a
:class:`WalletState` with realized PnL, open exposure, position concentration,
conviction and scaling. Replaying a wallet's swaps through this reducer rebuilds
its entire ``wallet_state(t)`` trajectory deterministically.
"""

from __future__ import annotations

from collections import deque

from ..schemas.common import Side
from ..schemas.state import WalletState
from ..schemas.swap import SwapEvent


class _Lot:
    __slots__ = ("tokens", "cost")

    def __init__(self, tokens: float, cost: float) -> None:
        self.tokens = tokens
        self.cost = cost


class WalletStateReducer:
    def __init__(self, address: str) -> None:
        self.address = address
        self._seq = 0
        self._lots: dict[str, deque[_Lot]] = {}
        self._realized = 0.0
        self._volume = 0.0
        self._trades = 0
        self._recent_buys: deque[float] = deque(maxlen=5)
        self._avg_buy = 0.0

    def apply(self, swap: SwapEvent) -> WalletState:
        self._trades += 1
        self._volume += swap.sol_amount
        mint = swap.token_address

        if swap.side == Side.buy:
            self._lots.setdefault(mint, deque()).append(_Lot(swap.token_amount, swap.sol_amount))
            self._recent_buys.append(swap.sol_amount)
            # running average buy size (for conviction)
            self._avg_buy += (swap.sol_amount - self._avg_buy) / min(self._trades, 50)
        else:  # sell: realize against oldest lots (FIFO)
            remaining = swap.token_amount
            proceeds_per = swap.sol_amount / swap.token_amount if swap.token_amount else 0.0
            lots = self._lots.get(mint)
            while lots and remaining > 1e-12:
                lot = lots[0]
                take = min(remaining, lot.tokens)
                frac = take / lot.tokens if lot.tokens else 0.0
                cost = lot.cost * frac
                self._realized += proceeds_per * take - cost
                lot.tokens -= take
                lot.cost -= cost
                remaining -= take
                if lot.tokens <= 1e-12:
                    lots.popleft()

        return self._emit(swap)

    def _emit(self, swap: SwapEvent) -> WalletState:
        # exposure + concentration across open mints
        exposures = {m: sum(l.cost for l in lots) for m, lots in self._lots.items()}
        exposures = {m: c for m, c in exposures.items() if c > 1e-9}
        total_exp = sum(exposures.values())
        herfindahl = (
            sum((c / total_exp) ** 2 for c in exposures.values()) if total_exp > 0 else 0.0
        )
        conviction = (swap.sol_amount / self._avg_buy) if self._avg_buy > 0 else 0.0
        scaling = 0.0
        if len(self._recent_buys) >= 2:
            first, last = self._recent_buys[0], self._recent_buys[-1]
            scaling = max(-1.0, min(1.0, (last - first) / (abs(first) + 1e-9)))

        self._seq += 1
        return WalletState(
            address=self.address,
            ts=swap.timestamp,
            seq=self._seq - 1,
            realized_pnl_sol=self._realized,
            exposure_sol=total_exp,
            open_positions=len(exposures),
            position_concentration=herfindahl,
            conviction=conviction,
            scaling=scaling,
            cumulative_volume_sol=self._volume,
            trade_count=self._trades,
        )
