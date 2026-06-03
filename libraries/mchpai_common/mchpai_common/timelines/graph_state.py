"""Incremental graph state reducer — graph(t).

Most graph stores are static; ours is temporal. This reducer records lightweight
metric snapshots of the evolving wallet graph (node/edge/cluster counts, density,
edge growth) so we can later train temporal GNNs on how structure *changes*.
"""

from __future__ import annotations

from datetime import datetime

from ..schemas.state import GraphState


class GraphStateReducer:
    def __init__(self) -> None:
        self._seq = 0
        self._prev_edges = 0

    def snapshot(
        self,
        ts: datetime,
        *,
        wallets: int,
        co_buy_edges: int,
        funded_edges: int,
        transfer_edges: int,
        clusters: int,
        top_cluster_score: float = 0.0,
    ) -> GraphState:
        total_edges = co_buy_edges + funded_edges + transfer_edges
        density = total_edges / wallets if wallets > 0 else 0.0
        delta = total_edges - self._prev_edges
        self._prev_edges = total_edges
        self._seq += 1
        return GraphState(
            ts=ts,
            seq=self._seq - 1,
            wallets=wallets,
            co_buy_edges=co_buy_edges,
            funded_edges=funded_edges,
            transfer_edges=transfer_edges,
            clusters=clusters,
            top_cluster_score=top_cluster_score,
            density=density,
            new_edges_delta=delta,
        )
