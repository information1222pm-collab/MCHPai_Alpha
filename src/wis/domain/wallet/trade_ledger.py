"""The trade ledger — exact, deterministic, quote-aware position accounting.

Buys open lots; sells consume them FIFO, each consumption crystallising a
:class:`ClosedTrade`. All arithmetic is rational (:class:`fractions.Fraction`)
so cost basis is exact across an unbounded history — no penny of drift, fully
replay-deterministic.

Lots are keyed by ``(token, quote)``: a position bought in SOL and a position in
the same token bought in USDC are tracked separately, and a buy in one quote can
never be matched against a sell in another. This keeps every ``multiple`` and
PnL quote-internal — SOL and USDC are never silently summed (Statistics Rule 1
extended to currency).

A :class:`ClosedTrade` is the fundamental observation of *behavior*: an entry,
an exit, what it cost, what it returned (in its quote), and how long conviction
was held.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from fractions import Fraction

from wis.domain.identifiers import TokenMint
from wis.domain.money import Amount
from wis.domain.time import Nanos, Sequence

# Default quote when an event does not specify one (native SOL trades).
DEFAULT_QUOTE = "SOL"


@dataclass(frozen=True, slots=True)
class ClosedTrade:
    """A completed round trip on some quantity of a token, in one quote asset."""

    token: TokenMint
    quote: str  # quote asset the cost/proceeds are denominated in (e.g. "SOL")
    qty: Fraction  # token units round-tripped
    cost: Fraction  # quote units paid to acquire this qty
    proceeds: Fraction  # quote units received on disposal
    entry_time: Nanos
    exit_time: Nanos
    entry_sequence: Sequence
    exit_sequence: Sequence

    @property
    def pnl(self) -> Fraction:
        return self.proceeds - self.cost

    @property
    def multiple(self) -> Fraction | None:
        """Proceeds-over-cost. ``None`` for a zero-cost (airdrop-like) basis."""
        return self.proceeds / self.cost if self.cost > 0 else None

    @property
    def trade_return(self) -> Fraction | None:
        m = self.multiple
        return m - 1 if m is not None else None

    @property
    def hold_nanos(self) -> int:
        return int(self.exit_time) - int(self.entry_time)

    @property
    def is_win(self) -> bool:
        return self.pnl > 0


@dataclass(frozen=True, slots=True)
class _Lot:
    qty: Fraction
    cost: Fraction
    entry_time: Nanos
    entry_sequence: Sequence


@dataclass(frozen=True, slots=True)
class OpenPosition:
    """Unrealised exposure to a token in a quote: the residue of unsold lots."""

    token: TokenMint
    quote: str
    qty: Fraction
    cost: Fraction
    first_entry_time: Nanos
    last_entry_time: Nanos

    @property
    def average_price(self) -> Fraction | None:
        return self.cost / self.qty if self.qty > 0 else None


_Key = tuple[TokenMint, str]


@dataclass(slots=True)
class TradeLedger:
    """Mutable-but-pure accumulator, advanced by ``buy`` / ``sell`` in event order,
    so its evolution is a deterministic function of the log."""

    closed: list[ClosedTrade] = field(default_factory=list)
    _open: dict[_Key, list[_Lot]] = field(default_factory=dict)
    # Sells that exceeded held inventory (dust / unseen acquisitions). Tracked,
    # never silently dropped — anomalies are signal, not noise.
    oversold_events: int = 0

    def buy(
        self,
        token: TokenMint,
        base: Amount,
        quote: Amount,
        at: Nanos,
        seq: Sequence,
        quote_mint: str = DEFAULT_QUOTE,
    ) -> None:
        qty = base.as_fraction()
        if qty <= 0:
            return
        lot = _Lot(qty=qty, cost=quote.as_fraction(), entry_time=at, entry_sequence=seq)
        self._open.setdefault((token, quote_mint), []).append(lot)

    def sell(
        self,
        token: TokenMint,
        base: Amount,
        quote: Amount,
        at: Nanos,
        seq: Sequence,
        quote_mint: str = DEFAULT_QUOTE,
    ) -> None:
        remaining = base.as_fraction()
        if remaining <= 0:
            return
        proceeds_total = quote.as_fraction()
        sell_qty_total = remaining
        lots = self._open.get((token, quote_mint), [])

        while remaining > 0 and lots:
            lot = lots[0]
            take = min(lot.qty, remaining)
            # Proceeds and cost are split proportionally to the quantity taken,
            # exactly, so partial fills never lose or invent value.
            proceeds = proceeds_total * (take / sell_qty_total)
            cost = lot.cost * (take / lot.qty)
            self.closed.append(
                ClosedTrade(
                    token=token,
                    quote=quote_mint,
                    qty=take,
                    cost=cost,
                    proceeds=proceeds,
                    entry_time=lot.entry_time,
                    exit_time=at,
                    entry_sequence=lot.entry_sequence,
                    exit_sequence=seq,
                )
            )
            remaining -= take
            if take == lot.qty:
                lots.pop(0)
            else:
                lots[0] = replace(lot, qty=lot.qty - take, cost=lot.cost - cost)

        if remaining > 0:
            # Sold more than we ever saw bought in this quote. Record the anomaly.
            self.oversold_events += 1

    def open_positions(self) -> list[OpenPosition]:
        positions: list[OpenPosition] = []
        for (token, quote_mint), lots in self._open.items():
            if not lots:
                continue
            qty = sum((lot.qty for lot in lots), Fraction(0))
            if qty <= 0:
                continue
            cost = sum((lot.cost for lot in lots), Fraction(0))
            positions.append(
                OpenPosition(
                    token=token,
                    quote=quote_mint,
                    qty=qty,
                    cost=cost,
                    first_entry_time=min(lot.entry_time for lot in lots),
                    last_entry_time=max(lot.entry_time for lot in lots),
                )
            )
        return positions
