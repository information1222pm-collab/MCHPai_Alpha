"""Point-in-time price context for *timing* intelligence.

To judge whether a wallet entered "early" or "cheap" we need the token's price
history — but only the part of it that was knowable at the moment of the trade.
This context accumulates observed prices in event order, so any percentile query
can be answered using strictly the prices seen *up to* the query instant. That
is what makes timing metrics leak-free: we never reward a wallet for buying
below a price the market had not yet printed.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field

from wis.domain.identifiers import TokenMint
from wis.domain.time import Nanos


@dataclass(slots=True)
class PriceContext:
    # token -> parallel arrays of (ascending observation time, price-at-that-time)
    _times: dict[TokenMint, list[Nanos]] = field(default_factory=dict)
    _prices: dict[TokenMint, list[float]] = field(default_factory=dict)
    first_seen: dict[TokenMint, Nanos] = field(default_factory=dict)

    def observe(self, token: TokenMint, price: float, at: Nanos) -> None:
        self._times.setdefault(token, []).append(at)
        self._prices.setdefault(token, []).append(price)
        self.first_seen.setdefault(token, at)

    def prices_up_to(self, token: TokenMint, until: Nanos) -> list[float]:
        """Prices observed for ``token`` at or before ``until`` — the only data a
        point-in-time timing feature is permitted to see."""
        times = self._times.get(token)
        if not times:
            return []
        cut = bisect_right(times, until)
        return self._prices[token][:cut]

    def genesis(self, token: TokenMint) -> Nanos | None:
        return self.first_seen.get(token)
