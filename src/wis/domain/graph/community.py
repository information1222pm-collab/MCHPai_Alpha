"""Deterministic Louvain community detection.

Communities are not assigned; they *emerge* from the co-buy graph by greedily
maximizing modularity. The charter names Louvain specifically. This is a pure,
dependency-free implementation tuned for one property above raw speed:
**determinism**. Nodes are always visited in a fixed (sorted) order and ties are
broken by community id, so the same graph always yields the same partition — a
hard requirement for replayable cluster history.

The algorithm: local moving (each node joins the neighbouring community that
best improves modularity) followed by aggregation into a coarser graph, repeated
until modularity stops improving.
"""

from __future__ import annotations

from collections import defaultdict

from wis.domain.graph.graph_state import WalletGraph
from wis.domain.identifiers import WalletAddress

Partition = dict[WalletAddress, int]


def louvain(graph: WalletGraph, *, max_passes: int = 20) -> Partition:
    """Return a mapping wallet -> community index over the co-buy graph."""
    nodes = sorted(graph.nodes, key=lambda w: w.value)
    if not nodes:
        return {}

    index = {w: i for i, w in enumerate(nodes)}
    # Adjacency as index -> {index -> weight}, including zero-degree nodes.
    adj: dict[int, dict[int, float]] = {i: {} for i in range(len(nodes))}
    for w, nbrs in graph.cobuy.items():
        i = index[w]
        for nb, wt in nbrs.items():
            adj[i][index[nb]] = wt

    partition = _solve(adj)
    # Map coarse community ids back onto wallet addresses, renumbered 0..k-1
    # in deterministic (sorted) order.
    raw = {nodes[i]: c for i, c in partition.items()}
    relabel = {c: r for r, c in enumerate(sorted(set(raw.values())))}
    return {w: relabel[c] for w, c in raw.items()}


def _solve(adj: dict[int, dict[int, float]]) -> dict[int, int]:
    node_to_comm = {i: i for i in adj}
    m2 = sum(w for nbrs in adj.values() for w in nbrs.values())  # 2m
    if m2 == 0:
        # No edges: every node is its own singleton community.
        return node_to_comm

    k = {i: sum(nbrs.values()) for i, nbrs in adj.items()}  # weighted degree
    sigma_tot = dict(k)  # total degree of each community

    improved = True
    while improved:
        improved = False
        for i in sorted(adj):
            ci = node_to_comm[i]
            ki = k[i]
            # Weight from i into each neighbouring community.
            comm_links: dict[int, float] = defaultdict(float)
            for j, w in adj[i].items():
                if j != i:
                    comm_links[node_to_comm[j]] += w

            # Remove i from its community.
            sigma_tot[ci] -= ki
            best_comm = ci
            best_gain = comm_links.get(ci, 0.0) - sigma_tot[ci] * ki / m2
            # Evaluate candidate communities in deterministic order.
            for comm in sorted(comm_links):
                gain = comm_links[comm] - sigma_tot[comm] * ki / m2
                if gain > best_gain + 1e-12:
                    best_gain = gain
                    best_comm = comm
            sigma_tot[best_comm] += ki
            if best_comm != ci:
                node_to_comm[i] = best_comm
                improved = True

    return node_to_comm


def modularity(graph: WalletGraph, partition: Partition) -> float:
    """Newman modularity of a partition — the quality the labs report on."""
    m2 = sum(w for nbrs in graph.cobuy.values() for w in nbrs.values())
    if m2 == 0:
        return 0.0
    q = 0.0
    deg = {w: sum(nbrs.values()) for w, nbrs in graph.cobuy.items()}
    for w, nbrs in graph.cobuy.items():
        for nb, wt in nbrs.items():
            if partition.get(w) == partition.get(nb):
                q += wt - deg[w] * deg.get(nb, 0.0) / m2
    return q / m2
