"""cluster_lab — community structure and its evolution.

Clusters are movies, not snapshots. This lab measures the partition at a point
in time and, by comparing two points, how membership *flows* between communities.
"""

from __future__ import annotations

from dataclasses import dataclass

from wis.app.observatory import Observatory
from wis.domain.identifiers import ClusterId, WalletAddress
from wis.domain.time import Nanos


@dataclass(frozen=True, slots=True)
class ClusterSnapshot:
    sizes: dict[str, int]
    modularity: float
    count: int


def snapshot(obs: Observatory, *, as_of: Nanos | None = None) -> ClusterSnapshot:
    clusters = obs.clusters(as_of=as_of)
    summary = obs.graph_summary(as_of=as_of)
    return ClusterSnapshot(
        sizes={cid.value: len(members) for cid, members in clusters.items()},
        modularity=summary.modularity,
        count=summary.cluster_count,
    )


@dataclass(frozen=True, slots=True)
class MembershipDrift:
    joined: dict[str, list[str]]  # cluster -> wallets that entered it
    left: dict[str, list[str]]  # cluster -> wallets that exited it


def membership_drift(obs: Observatory, *, earlier: Nanos, later: Nanos) -> MembershipDrift:
    """How wallets moved between communities from ``earlier`` to ``later``."""
    def membership(as_of: Nanos) -> dict[WalletAddress, ClusterId]:
        out: dict[WalletAddress, ClusterId] = {}
        for cid, members in obs.clusters(as_of=as_of).items():
            for w in members:
                out[w] = cid
        return out

    before = membership(earlier)
    after = membership(later)
    joined: dict[str, list[str]] = {}
    left: dict[str, list[str]] = {}
    for w, cid in after.items():
        if before.get(w) != cid:
            joined.setdefault(cid.value, []).append(w.value)
    for w, cid in before.items():
        if after.get(w) != cid:
            left.setdefault(cid.value, []).append(w.value)
    return MembershipDrift(joined=joined, left=left)
