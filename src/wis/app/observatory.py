"""The Observatory — the application facade over the intelligence core.

This is the seam the API, the research labs and future ML pipelines all talk to.
It owns an :class:`EventStore` and composes the projections, feature factory,
scoring and graph intelligence into a few coherent queries:

* ``ingest`` a world fact into the log.
* observe ``wallet_frame`` / ``wallet_scores`` / ``features`` at any point in time.
* observe ``graph`` and ``clusters``.
* ``emit_intelligence`` — replay the world and write the system's *conclusions*
  back into the log as derived events, so the reasoning itself is replayable.

Build the observatory first. Prediction and execution emerge later — and there
is deliberately none of either here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from wis.domain.events import (
    ClusterDetected,
    DomainEvent,
    GraphUpdated,
    WalletAlphaUpdated,
    WalletProfileGenerated,
    WalletStateUpdated,
)
from wis.domain.graph.community import louvain, modularity
from wis.domain.graph.metrics import GraphSummary, GraphWalletMetrics, compute_graph_metrics
from wis.domain.identifiers import ClusterId, WalletAddress
from wis.domain.time import Nanos, Sequence
from wis.domain.wallet.state import WalletFrame
from wis.eventsourcing.event import StoredEvent
from wis.eventsourcing.replay import ReplayEngine
from wis.eventsourcing.store import EventStore, InMemoryEventStore
from wis.features.compiler import FeatureCompiler, FeatureVector
from wis.projections.graph_projector import GraphProjector, GraphWorld
from wis.projections.wallet_projector import WalletProjector, WalletWorld
from wis.scoring.scores import WalletScores, score_wallet

if TYPE_CHECKING:
    from wis.sources.base import Source


@dataclass(frozen=True, slots=True)
class WalletReport:
    """The complete intelligence picture for one wallet at a point in time."""

    frame: WalletFrame
    scores: WalletScores
    features: FeatureVector
    graph: GraphWalletMetrics | None


class Observatory:
    def __init__(self, store: EventStore | None = None) -> None:
        self._store: EventStore = store if store is not None else InMemoryEventStore()
        self._compiler = FeatureCompiler()

    @property
    def store(self) -> EventStore:
        return self._store

    # -- ingestion ---------------------------------------------------------

    def ingest(self, payload: DomainEvent, *, ingestion_time: Nanos | None = None) -> StoredEvent:
        return self._store.append(payload, ingestion_time=ingestion_time)

    def ingest_source(self, source: Source, *, limit: int | None = None) -> int:
        """Pump a reality source into the log — the one door. Any source
        (archive, Helius, Yellowstone, RPC, CSV, synthetic) lands here as the
        same domain events. Returns the number of events ingested."""
        from wis.sources.base import pump

        return pump(source, self._store, limit=limit)

    # -- point-in-time worlds ---------------------------------------------

    def wallet_world(self, *, up_to: Sequence | None = None, as_of: Nanos | None = None) -> WalletWorld:
        return ReplayEngine(self._store, WalletProjector()).run(up_to=up_to, as_of=as_of)

    def graph_world(self, *, up_to: Sequence | None = None, as_of: Nanos | None = None) -> GraphWorld:
        return ReplayEngine(self._store, GraphProjector()).run(up_to=up_to, as_of=as_of)

    # -- wallet intelligence ----------------------------------------------

    def wallet_frame(
        self, address: WalletAddress, *, up_to: Sequence | None = None, as_of: Nanos | None = None
    ) -> WalletFrame | None:
        world = self.wallet_world(up_to=up_to, as_of=as_of)
        ws = world.get(address)
        return ws.frame(prices=world.prices) if ws is not None else None

    def wallet_report(
        self, address: WalletAddress, *, up_to: Sequence | None = None, as_of: Nanos | None = None
    ) -> WalletReport | None:
        world = self.wallet_world(up_to=up_to, as_of=as_of)
        ws = world.get(address)
        if ws is None:
            return None
        frame = ws.frame(prices=world.prices)

        # Fold in the social dimension from graph(t), if the wallet appears there.
        graph_world = self.graph_world(up_to=up_to, as_of=as_of)
        gmetrics = self._graph_metrics(graph_world).get(address)

        scores = score_wallet(frame, gmetrics)
        features = self._compiler.compile(frame)
        return WalletReport(frame=frame, scores=scores, features=features, graph=gmetrics)

    def list_wallets(self, *, up_to: Sequence | None = None, as_of: Nanos | None = None) -> list[WalletAddress]:
        return sorted(self.wallet_world(up_to=up_to, as_of=as_of).wallets, key=lambda w: w.value)

    # -- graph intelligence -----------------------------------------------

    def clusters(
        self, *, up_to: Sequence | None = None, as_of: Nanos | None = None
    ) -> dict[ClusterId, list[WalletAddress]]:
        graph_world = self.graph_world(up_to=up_to, as_of=as_of)
        partition = louvain(graph_world.graph)
        out: dict[ClusterId, list[WalletAddress]] = {}
        for wallet, comm in partition.items():
            out.setdefault(ClusterId(f"c{comm}"), []).append(wallet)
        for members in out.values():
            members.sort(key=lambda w: w.value)
        return out

    def graph_summary(self, *, up_to: Sequence | None = None, as_of: Nanos | None = None) -> GraphSummary:
        graph_world = self.graph_world(up_to=up_to, as_of=as_of)
        g = graph_world.graph
        partition = louvain(g)
        return GraphSummary(
            node_count=g.node_count,
            edge_count=g.edge_count,
            density=g.density,
            cluster_count=len(set(partition.values())),
            modularity=modularity(g, partition),
        )

    @staticmethod
    def _graph_metrics(graph_world: GraphWorld) -> dict[WalletAddress, GraphWalletMetrics]:
        return compute_graph_metrics(graph_world.graph, louvain(graph_world.graph))

    # -- the system thinking out loud -------------------------------------

    def emit_intelligence(self, *, at: Nanos) -> list[StoredEvent]:
        """Replay the world and append the system's conclusions as derived
        events. This makes intelligence a first-class, replayable part of the
        log — not a side effect hidden in a database."""
        emitted: list[StoredEvent] = []
        world = self.wallet_world()
        graph_world = self.graph_world()
        gmetrics = self._graph_metrics(graph_world)

        for address in sorted(world.wallets, key=lambda w: w.value):
            ws = world.wallets[address]
            frame = ws.frame(prices=world.prices)
            scores = score_wallet(frame, gmetrics.get(address))

            emitted.append(
                self.ingest(
                    WalletStateUpdated(
                        occurred_at=at,
                        wallet=address,
                        closed_trades=frame.sample_size,
                        open_positions=len(ws.open_positions()),
                    ),
                    ingestion_time=at,
                )
            )
            if scores.wallet_alpha_score is not None:
                emitted.append(
                    self.ingest(
                        WalletAlphaUpdated(occurred_at=at, wallet=address, alpha_score=scores.wallet_alpha_score),
                        ingestion_time=at,
                    )
                )
            emitted.append(
                self.ingest(
                    WalletProfileGenerated(occurred_at=at, wallet=address, summary=frame.dna.summary()),
                    ingestion_time=at,
                )
            )

        # Cluster + graph conclusions.
        for cluster, members in self.clusters().items():
            emitted.append(
                self.ingest(
                    ClusterDetected(occurred_at=at, cluster=cluster, members=tuple(members)),
                    ingestion_time=at,
                )
            )
        summary = self.graph_summary()
        emitted.append(
            self.ingest(
                GraphUpdated(
                    occurred_at=at,
                    node_count=summary.node_count,
                    edge_count=summary.edge_count,
                    density=summary.density,
                    cluster_count=summary.cluster_count,
                ),
                ingestion_time=at,
            )
        )
        return emitted
