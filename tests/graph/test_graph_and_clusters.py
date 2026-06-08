"""The graph captures funding lineage and co-buy coordination, and Louvain
recovers planted communities deterministically."""

from __future__ import annotations

from tests.conftest import Scenario
from wis.domain.graph.community import louvain, modularity
from wis.domain.graph.metrics import compute_graph_metrics
from wis.domain.identifiers import WalletAddress
from wis.eventsourcing.replay import ReplayEngine
from wis.eventsourcing.store import InMemoryEventStore
from wis.projections.graph_projector import GraphProjector


def _two_cliques() -> InMemoryEventStore:
    """Two groups that each co-buy their own tokens; one funder seeds group A."""
    store = InMemoryEventStore()
    s = Scenario(store)
    group_a = ["a1", "a2", "a3"]
    group_b = ["b1", "b2", "b3"]
    for w in group_a + group_b:
        s.created(w)
    s.funded("a1", "a2", 5.0)
    s.funded("a1", "a3", 5.0)
    # Group A co-buys tokens TA*, group B co-buys TB*, within the co-buy window.
    for tok in ["TA1", "TA2"]:
        for w in group_a:
            s.buy(w, tok, base=10, quote=0.1, advance=60_000_000_000)  # 1 min apart
    for tok in ["TB1", "TB2"]:
        for w in group_b:
            s.buy(w, tok, base=10, quote=0.1, advance=60_000_000_000)
    return store


def test_funding_lineage_is_tracked() -> None:
    world = ReplayEngine(_two_cliques(), GraphProjector()).run()
    g = world.graph
    assert WalletAddress("a2") in g.funding_out[WalletAddress("a1")]
    assert g.funding_roots()[0] == WalletAddress("a1") or WalletAddress("a1") in g.funding_roots()


def test_louvain_recovers_two_communities() -> None:
    world = ReplayEngine(_two_cliques(), GraphProjector()).run()
    part = louvain(world.graph)
    a_comm = {part[WalletAddress(w)] for w in ["a1", "a2", "a3"]}
    b_comm = {part[WalletAddress(w)] for w in ["b1", "b2", "b3"]}
    assert len(a_comm) == 1 and len(b_comm) == 1
    assert a_comm != b_comm  # the two groups separate
    assert modularity(world.graph, part) > 0.0


def test_louvain_is_deterministic() -> None:
    world = ReplayEngine(_two_cliques(), GraphProjector()).run()
    assert louvain(world.graph) == louvain(world.graph)


def test_graph_metrics_expose_influence_and_cluster() -> None:
    world = ReplayEngine(_two_cliques(), GraphProjector()).run()
    part = louvain(world.graph)
    metrics = compute_graph_metrics(world.graph, part)
    a1 = metrics[WalletAddress("a1")]
    assert a1.funding_out_degree == 2
    assert 0.0 <= a1.influence_score <= 1.0
    assert a1.cluster is not None
