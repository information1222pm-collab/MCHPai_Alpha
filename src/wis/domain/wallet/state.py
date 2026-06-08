"""``wallet_state(t)`` — a wallet as a movie frame.

This is the central read model of the system: a wallet's identity plus the full
quantitative and qualitative picture of its behavior *as of* a particular point
in the log. It is always produced by replaying the event log into a
:class:`~wis.projections.wallet_projector.WalletProjector`; it is never mutated
in place. Two replays of the same log produce identical states.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from wis.domain.identifiers import WalletAddress
from wis.domain.time import Nanos, Sequence
from wis.domain.wallet.dna import WalletDNA
from wis.domain.wallet.metrics import (
    ConvictionMetrics,
    MetricInputs,
    PerformanceMetrics,
    RiskMetrics,
    TimingMetrics,
)
from wis.domain.wallet.price_context import PriceContext
from wis.domain.wallet.trade_ledger import OpenPosition, TradeLedger


@dataclass(slots=True)
class WalletState:
    """The materialized view of a single wallet at a point in time.

    Holds the raw ledger (the accumulator the projector advances) plus the
    derived metrics + DNA, which are recomputed from the ledger on demand via
    :meth:`refresh`. Keeping raw and derived separate means the expensive metric
    pass runs only when a consumer actually asks for a frame.
    """

    address: WalletAddress
    created_at: Nanos
    funded_by: WalletAddress | None = None

    # Bookkeeping that ties the state to an exact position in the log.
    last_sequence: Sequence = Sequence(0)
    last_event_time: Nanos = Nanos(0)
    buy_count: int = 0
    sell_count: int = 0

    ledger: TradeLedger = field(default_factory=TradeLedger)
    attributes: dict[str, str] = field(default_factory=dict)

    @property
    def closed_trade_count(self) -> int:
        return len(self.ledger.closed)

    def open_positions(self) -> list[OpenPosition]:
        return self.ledger.open_positions()

    # -- Derived view ------------------------------------------------------

    def frame(self, *, reference_time: Nanos | None = None, prices: PriceContext | None = None) -> WalletFrame:
        """Produce the fully-derived intelligence frame for this wallet.

        ``reference_time`` is the "now" used for windowed metrics (defaults to
        the wallet's last event time). ``prices`` supplies point-in-time price
        context for timing intelligence.
        """
        ref = reference_time if reference_time is not None else self.last_event_time
        mi = MetricInputs(
            closed=self.ledger.closed,
            positions=self.open_positions(),
            reference_time=ref,
            buy_count=self.buy_count,
            sell_count=self.sell_count,
            price_context=prices,
        )
        performance = PerformanceMetrics.compute(mi)
        timing = TimingMetrics.compute(mi)
        conviction = ConvictionMetrics.compute(mi)
        risk = RiskMetrics.compute(mi)
        dna = WalletDNA.sequence(performance, timing, conviction, risk)
        return WalletFrame(
            address=self.address,
            as_of_sequence=self.last_sequence,
            as_of_time=self.last_event_time,
            sample_size=len(self.ledger.closed),
            performance=performance,
            timing=timing,
            conviction=conviction,
            risk=risk,
            dna=dna,
        )


@dataclass(frozen=True, slots=True)
class WalletFrame:
    """An immutable snapshot of the derived intelligence for a wallet at ``t``.

    A *frame* of the movie: pin it, compare two of them, and you can watch a
    wallet evolve.
    """

    address: WalletAddress
    as_of_sequence: Sequence
    as_of_time: Nanos
    sample_size: int  # closed-trade count — the evidence backing every metric
    performance: PerformanceMetrics
    timing: TimingMetrics
    conviction: ConvictionMetrics
    risk: RiskMetrics
    dna: WalletDNA
