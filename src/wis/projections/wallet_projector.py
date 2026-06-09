"""WalletProjector — folds the event log into ``wallet_state(t)`` for every wallet.

The projection state is a :class:`WalletWorld`: a registry of per-wallet
:class:`WalletState` accumulators plus a shared :class:`PriceContext`. The fold
is advanced strictly in sequence order, so the world's evolution is a pure,
replay-deterministic function of the log. Stop the replay at any sequence (or
``as_of`` instant) and you have the entire wallet universe as it stood then.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from wis.domain.events import (
    TokenPriceObserved,
    WalletBoughtToken,
    WalletCreated,
    WalletFunded,
    WalletSoldToken,
    WalletUpdated,
)
from wis.domain.identifiers import WalletAddress
from wis.domain.wallet.price_context import PriceContext
from wis.domain.wallet.state import WalletState
from wis.eventsourcing.event import StoredEvent


@dataclass(slots=True)
class WalletWorld:
    wallets: dict[WalletAddress, WalletState] = field(default_factory=dict)
    prices: PriceContext = field(default_factory=PriceContext)

    def get(self, address: WalletAddress) -> WalletState | None:
        return self.wallets.get(address)


class WalletProjector:
    """Pure fold: ``(WalletWorld, StoredEvent) -> WalletWorld``."""

    def initial(self) -> WalletWorld:
        return WalletWorld()

    def apply(self, state: WalletWorld, event: StoredEvent) -> WalletWorld:
        payload = event.payload

        if isinstance(payload, WalletCreated):
            self._ensure(state, payload.wallet, event)
            ws = state.wallets[payload.wallet]
            if payload.funded_by is not None:
                ws.funded_by = payload.funded_by

        elif isinstance(payload, WalletFunded):
            # Funding both *creates* awareness of a wallet and records lineage.
            self._ensure(state, payload.target, event)
            state.wallets[payload.target].funded_by = payload.source
            self._ensure(state, payload.source, event)

        elif isinstance(payload, WalletBoughtToken):
            ws = self._ensure(state, payload.wallet, event)
            ws.ledger.buy(
                payload.token, payload.base, payload.quote, payload.occurred_at,
                event.sequence, quote_mint=payload.quote_mint,
            )
            ws.buy_count += 1
            self._touch(ws, event)

        elif isinstance(payload, WalletSoldToken):
            ws = self._ensure(state, payload.wallet, event)
            ws.ledger.sell(
                payload.token, payload.base, payload.quote, payload.occurred_at,
                event.sequence, quote_mint=payload.quote_mint,
            )
            ws.sell_count += 1
            self._touch(ws, event)

        elif isinstance(payload, TokenPriceObserved):
            state.prices.observe(
                payload.token,
                float(payload.price_quote_per_base.as_fraction()),
                payload.occurred_at,
            )

        elif isinstance(payload, WalletUpdated):
            ws = self._ensure(state, payload.wallet, event)
            ws.attributes.update(payload.attributes)

        # Derived events (WalletStateUpdated, alpha, clusters, graph, profiles)
        # are conclusions emitted *by* projections, not inputs to this one;
        # ignoring them keeps the fold idempotent under re-emission.
        return state

    @staticmethod
    def _ensure(state: WalletWorld, address: WalletAddress, event: StoredEvent) -> WalletState:
        ws = state.wallets.get(address)
        if ws is None:
            ws = WalletState(address=address, created_at=event.event_time)
            state.wallets[address] = ws
        return ws

    @staticmethod
    def _touch(ws: WalletState, event: StoredEvent) -> None:
        ws.last_sequence = event.sequence
        ws.last_event_time = event.event_time
