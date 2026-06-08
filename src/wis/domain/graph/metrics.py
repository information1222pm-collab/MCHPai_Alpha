"""Graph-derived wallet metrics — the *social* dimension of intelligence.

Influence, centrality and cluster participation are properties a wallet has only
by virtue of its relationships, so they are computed from ``graph(t)`` rather
than from the wallet's own ledger. These feed the social scores
(``influence_score``, ``cluster_score``) and, eventually, graph neural networks.
"""

from __future__ import annotations

from dataclasses import dataclass

from wis.domain.graph.community import Partition
from wis.domain.graph.graph_state import WalletGraph
from wis.domain.identifiers import ClusterId, WalletAddress


@dataclass(frozen=True, slots=True)
class GraphWalletMetrics:
    address: WalletAddress
    degree: int  # number of co-buy neighbours
    weighted_degree: float  # summed co-buy strength
    degree_centrality: float  # degree / (N-1), in [0,1]
    funding_out_degree: int  # wallets this one seeded
    funding_in_degree: int  # wallets that seeded this one
    cluster: ClusterId | None
    cluster_size: int
    cluster_participation: float  # fraction of edge weight kept inside cluster
    influence_score: float  # normalized blend of reach (centrality + funding)
    cluster_score: float  # how central this wallet is within its community


@dataclass(frozen=True, slots=True)
class GraphSummary:
    node_count: int
    edge_count: int
    density: float
    cluster_count: int
    modularity: float


def compute_graph_metrics(
    graph: WalletGraph,
    partition: Partition,
) -> dict[WalletAddress, GraphWalletMetrics]:
    n = graph.node_count
    cluster_sizes: dict[int, int] = {}
    for c in partition.values():
        cluster_sizes[c] = cluster_sizes.get(c, 0) + 1

    max_wdeg = max(
        (sum(nbrs.values()) for nbrs in graph.cobuy.values()),
        default=0.0,
    )
    max_funding = max((len(t) for t in graph.funding_out.values()), default=0)

    out: dict[WalletAddress, GraphWalletMetrics] = {}
    for w in sorted(graph.nodes, key=lambda x: x.value):
        nbrs = graph.cobuy.get(w, {})
        degree = len(nbrs)
        wdeg = sum(nbrs.values())
        centrality = degree / (n - 1) if n > 1 else 0.0
        fout = len(graph.funding_out.get(w, set()))
        fin = len(graph.funding_in.get(w, set()))

        comm = partition.get(w)
        inside = sum(wt for nb, wt in nbrs.items() if partition.get(nb) == comm)
        participation = (inside / wdeg) if wdeg > 0 else 0.0

        # Reach: balance of how connected you are and how many wallets you seed.
        reach = 0.5 * (wdeg / max_wdeg if max_wdeg > 0 else 0.0)
        reach += 0.5 * (fout / max_funding if max_funding > 0 else 0.0)

        out[w] = GraphWalletMetrics(
            address=w,
            degree=degree,
            weighted_degree=wdeg,
            degree_centrality=centrality,
            funding_out_degree=fout,
            funding_in_degree=fin,
            cluster=ClusterId(f"c{comm}") if comm is not None else None,
            cluster_size=cluster_sizes.get(comm, 0) if comm is not None else 0,
            cluster_participation=participation,
            influence_score=reach,
            # Centrality within your own community = participation tempered by reach.
            cluster_score=0.5 * participation + 0.5 * reach,
        )
    return out
