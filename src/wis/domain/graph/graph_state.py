"""``graph(t)`` — the relationship structure of the wallet universe.

Participants are causes, and causes are entangled: wallets fund one another and
buy the same tokens at the same time. This module materializes those relations
as a weighted graph at a point in time. Two relation types are tracked:

* **Funding edges** (directed): who seeded whom. The raw material of funding
  trees and Sybil structures.
* **Co-buy edges** (undirected, weighted): how often two wallets bought the same
  token within a short window — a proxy for coordination / shared information.

Like everything else, ``graph(t)`` is a frame of a movie: rebuilt by replay,
never mutated behind the system's back. Communities (clusters) are derived from
it, and clusters too are movies — stable ids over evolving membership.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from wis.domain.identifiers import WalletAddress


@dataclass(slots=True)
class WalletGraph:
    # Undirected co-buy similarity: address -> {neighbor -> weight}. Symmetric.
    cobuy: dict[WalletAddress, dict[WalletAddress, float]] = field(default_factory=dict)
    # Directed funding lineage: source -> set(targets).
    funding_out: dict[WalletAddress, set[WalletAddress]] = field(default_factory=dict)
    funding_in: dict[WalletAddress, set[WalletAddress]] = field(default_factory=dict)
    nodes: set[WalletAddress] = field(default_factory=set)

    def add_node(self, w: WalletAddress) -> None:
        self.nodes.add(w)
        self.cobuy.setdefault(w, {})

    def add_funding(self, source: WalletAddress, target: WalletAddress) -> None:
        self.add_node(source)
        self.add_node(target)
        self.funding_out.setdefault(source, set()).add(target)
        self.funding_in.setdefault(target, set()).add(source)

    def bump_cobuy(self, a: WalletAddress, b: WalletAddress, weight: float = 1.0) -> None:
        if a == b:
            return
        self.add_node(a)
        self.add_node(b)
        self.cobuy[a][b] = self.cobuy[a].get(b, 0.0) + weight
        self.cobuy[b][a] = self.cobuy[b].get(a, 0.0) + weight

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return sum(len(nbrs) for nbrs in self.cobuy.values()) // 2

    @property
    def density(self) -> float:
        n = self.node_count
        if n < 2:
            return 0.0
        return 2.0 * self.edge_count / (n * (n - 1))

    def funding_roots(self) -> list[WalletAddress]:
        """Wallets that funded others but were funded by none — tree roots."""
        return sorted(
            (w for w in self.funding_out if not self.funding_in.get(w)),
            key=lambda w: w.value,
        )
