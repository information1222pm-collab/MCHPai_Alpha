"""Windowed snapshot aggregation.

A :class:`WindowAggregator` is created per (mint, window). It accepts swaps in
(approximately) time order and emits a :class:`TokenSnapshot` each time a window
boundary is crossed, carrying forward the last price so gaps produce valid
candles. Intelligence metrics that need external context (smart-money / cluster
ratios) are supplied via optional lookups so the aggregator stays pure.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from ..entropy import buyer_entropy
from ..indicators import gini
from ..schemas.common import Side
from ..schemas.snapshot import TokenSnapshot, Window
from ..schemas.swap import SwapEvent

AlphaLookup = Callable[[str], float]   # wallet -> alpha score (0..100)
ClusterLookup = Callable[[str], bool]  # wallet -> is in a known cluster


def _bucket(ts: datetime, seconds: int) -> int:
    return int(ts.timestamp()) // seconds


class WindowAggregator:
    def __init__(
        self,
        mint: str,
        window: Window,
        birth_ts: datetime,
        *,
        alpha_lookup: AlphaLookup | None = None,
        cluster_lookup: ClusterLookup | None = None,
    ) -> None:
        self.mint = mint
        self.window = window
        self.birth_ts = birth_ts
        self._alpha = alpha_lookup
        self._cluster = cluster_lookup
        self._seconds = window.seconds
        self._seq = 0
        self._last_close: float | None = None
        self._cur_bucket: int | None = None
        self._reset_bucket()

    def _reset_bucket(self) -> None:
        self._open = self._high = self._low = self._close = None
        self._volume = 0.0
        self._net_flow = 0.0
        self._buyers: set[str] = set()
        self._sellers: set[str] = set()
        self._traders: set[str] = set()
        self._txns = 0
        self._buyer_sol: dict[str, float] = {}
        self._smart_buy_vol = 0.0
        self._cluster_vol = 0.0
        self._last_mcap: float | None = None

    def add(self, swap: SwapEvent) -> list[TokenSnapshot]:
        """Add a swap; return any snapshots completed by this swap's arrival."""
        b = _bucket(swap.timestamp, self._seconds)
        out: list[TokenSnapshot] = []
        if self._cur_bucket is None:
            self._cur_bucket = b
        while b > self._cur_bucket:
            out.append(self._close_bucket(self._cur_bucket))
            self._cur_bucket += 1
            self._reset_bucket()
        self._accumulate(swap)
        return out

    def _accumulate(self, s: SwapEvent) -> None:
        px = s.price
        if px is not None:
            if self._open is None:
                self._open = px
            self._high = px if self._high is None else max(self._high, px)
            self._low = px if self._low is None else min(self._low, px)
            self._close = px
        self._volume += s.sol_amount
        self._txns += 1
        self._traders.add(s.wallet_address)
        if s.market_cap is not None:
            self._last_mcap = s.market_cap
        if s.side == Side.buy:
            self._buyers.add(s.wallet_address)
            self._net_flow += s.sol_amount
            self._buyer_sol[s.wallet_address] = self._buyer_sol.get(s.wallet_address, 0.0) + s.sol_amount
            if self._alpha and self._alpha(s.wallet_address) >= 70:
                self._smart_buy_vol += s.sol_amount
            if self._cluster and self._cluster(s.wallet_address):
                self._cluster_vol += s.sol_amount
        else:
            self._sellers.add(s.wallet_address)
            self._net_flow -= s.sol_amount

    def _close_bucket(self, bucket: int) -> TokenSnapshot:
        close_ts = datetime.fromtimestamp((bucket + 1) * self._seconds, tz=timezone.utc)
        close = self._close if self._close is not None else self._last_close
        self._last_close = close
        smart_ratio = (self._smart_buy_vol / self._volume) if self._volume > 0 else None
        cluster_ratio = (self._cluster_vol / self._volume) if self._volume > 0 else None
        snap = TokenSnapshot(
            mint=self.mint,
            window=self.window,
            ts=close_ts,
            seq=self._seq,
            age_seconds=max(0.0, close_ts.timestamp() - self.birth_ts.timestamp()),
            price_sol=close,
            open_sol=self._open,
            high_sol=self._high,
            low_sol=self._low,
            close_sol=close,
            volume_sol=self._volume,
            market_cap_sol=self._last_mcap,
            buyers=len(self._buyers),
            sellers=len(self._sellers),
            unique_traders=len(self._traders),
            txns=self._txns,
            net_flow_sol=self._net_flow,
            entropy=buyer_entropy(self._buyer_sol) if self._buyer_sol else 0.0,
            smart_money_ratio=smart_ratio,
            cluster_ratio=cluster_ratio,
        )
        self._seq += 1
        return snap

    def flush(self) -> list[TokenSnapshot]:
        """Close the in-progress bucket (call when the token goes quiet)."""
        if self._cur_bucket is None or self._txns == 0:
            return []
        snap = self._close_bucket(self._cur_bucket)
        self._cur_bucket += 1
        self._reset_bucket()
        return [snap]


class MultiWindowAggregator:
    """Fan a token's swaps into all four window resolutions at once."""

    def __init__(self, mint: str, birth_ts: datetime, **lookups) -> None:
        self.aggs = {w: WindowAggregator(mint, w, birth_ts, **lookups) for w in Window}

    def add(self, swap: SwapEvent) -> dict[Window, list[TokenSnapshot]]:
        return {w: agg.add(swap) for w, agg in self.aggs.items()}

    def flush(self) -> dict[Window, list[TokenSnapshot]]:
        return {w: agg.flush() for w, agg in self.aggs.items()}
