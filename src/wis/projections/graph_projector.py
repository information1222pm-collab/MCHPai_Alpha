"""GraphProjector — folds the event log into ``graph(t)``.

Funding events lay down directed lineage edges. Buys are accumulated per token;
when a wallet buys a token another wallet bought within the co-buy window, an
undirected co-buy edge is strengthened. The window makes the relation *temporal*:
buying the same token a year apart is coincidence, buying it in the same hour is
signal. The fold is pure and ordered, so the graph is replay-deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from wis.domain.events import (
    WalletBoughtToken,
    WalletCreated,
    WalletFunded,
)
from wis.domain.graph.graph_state import WalletGraph
from wis.domain.identifiers import TokenMint, WalletAddress
from wis.domain.time import HOUR, Nanos
from wis.eventsourcing.event import StoredEvent

# Two wallets buying the same token within this window are considered to be
# co-acting. Wide enough to catch coordinated entries, narrow enough to exclude
# unrelated later buyers.
DEFAULT_COBUY_WINDOW: int = 6 * HOUR


@dataclass(slots=True)
class GraphWorld:
    graph: WalletGraph = field(default_factory=WalletGraph)
    cobuy_window: int = DEFAULT_COBUY_WINDOW
    # token -> recent buyers as (wallet, event_time), pruned to the window.
    _recent: dict[TokenMint, list[tuple[WalletAddress, Nanos]]] = field(default_factory=dict)


class GraphProjector:
    def initial(self) -> GraphWorld:
        return GraphWorld()

    def apply(self, state: GraphWorld, event: StoredEvent) -> GraphWorld:
        payload = event.payload

        if isinstance(payload, WalletCreated):
            state.graph.add_node(payload.wallet)
            if payload.funded_by is not None:
                state.graph.add_funding(payload.funded_by, payload.wallet)

        elif isinstance(payload, WalletFunded):
            state.graph.add_funding(payload.source, payload.target)

        elif isinstance(payload, WalletBoughtToken):
            self._record_cobuy(state, payload.wallet, payload.token, payload.occurred_at)

        return state

    @staticmethod
    def _record_cobuy(
        state: GraphWorld,
        wallet: WalletAddress,
        token: TokenMint,
        at: Nanos,
    ) -> None:
        recent = state._recent.setdefault(token, [])
        cutoff = at - state.cobuy_window
        # Prune buyers outside the window (events arrive in time order).
        kept = [(w, t) for (w, t) in recent if t >= cutoff]
        for other, _ in kept:
            if other != wallet:
                state.graph.bump_cobuy(wallet, other, 1.0)
        kept.append((wallet, at))
        state._recent[token] = kept
