"""graph_lab — funding trees, density, and centrality leaders."""

from __future__ import annotations

from dataclasses import dataclass

from wis.app.observatory import Observatory
from wis.domain.graph.community import louvain
from wis.domain.graph.metrics import compute_graph_metrics
from wis.domain.identifiers import WalletAddress
from wis.domain.time import Nanos


@dataclass(frozen=True, slots=True)
class CentralityLeader:
    address: WalletAddress
    influence_score: float
    weighted_degree: float
    funding_out_degree: int


def influence_leaders(obs: Observatory, *, limit: int = 10, as_of: Nanos | None = None) -> list[CentralityLeader]:
    gw = obs.graph_world(as_of=as_of)
    metrics = compute_graph_metrics(gw.graph, louvain(gw.graph))
    leaders = [
        CentralityLeader(
            address=m.address,
            influence_score=m.influence_score,
            weighted_degree=m.weighted_degree,
            funding_out_degree=m.funding_out_degree,
        )
        for m in metrics.values()
    ]
    leaders.sort(key=lambda c: c.influence_score, reverse=True)
    return leaders[:limit]


def funding_tree(obs: Observatory, root: WalletAddress, *, as_of: Nanos | None = None) -> dict[str, list[str]]:
    """Breadth-first expansion of who ``root`` (transitively) funded."""
    gw = obs.graph_world(as_of=as_of)
    out: dict[str, list[str]] = {}
    seen: set[WalletAddress] = set()
    frontier = [root]
    while frontier:
        node = frontier.pop(0)
        if node in seen:
            continue
        seen.add(node)
        children = sorted(gw.graph.funding_out.get(node, set()), key=lambda w: w.value)
        out[node.value] = [c.value for c in children]
        frontier.extend(children)
    return out
