"""Cluster detection: community detection + coordination validation.

Pipeline:
  1. Project a weighted wallet graph in Neo4j GDS (CO_BOUGHT + FUNDED + TRANSFER).
  2. Run Louvain to get candidate communities.
  3. Validate each community with two coordination tests:
       - shared funding ancestry (a common funder within N hops)
       - co-buy *lift* vs. a random baseline (are co-buys non-coincidental?)
  4. Score the cluster (members' alpha × coordination strength).

The GDS calls are written as Cypher so they run server-side at graph scale.
"""

from __future__ import annotations

from mchpai_common.database import get_neo4j
from mchpai_common.logging import get_logger

log = get_logger("graph-engine.clustering")

PROJECT = """
CALL gds.graph.project.cypher(
  'wallets',
  'MATCH (w:Wallet) RETURN id(w) AS id',
  'MATCH (a:Wallet)-[r:CO_BOUGHT|FUNDED|TRANSFERRED]->(b:Wallet)
     RETURN id(a) AS source, id(b) AS target, count(r) AS weight'
) YIELD graphName
"""

LOUVAIN = """
CALL gds.louvain.stream('wallets', {relationshipWeightProperty:'weight'})
YIELD nodeId, communityId
RETURN gds.util.asNode(nodeId).address AS address, communityId
ORDER BY communityId
"""

DROP = "CALL gds.graph.drop('wallets', false) YIELD graphName"


async def detect_communities() -> dict[int, list[str]]:
    driver = get_neo4j()
    communities: dict[int, list[str]] = {}
    async with driver.session() as s:
        try:
            await s.run(DROP)
        except Exception:
            pass
        await s.run(PROJECT)
        result = await s.run(LOUVAIN)
        async for rec in result:
            communities.setdefault(int(rec["communityId"]), []).append(rec["address"])
        await s.run(DROP)
    return communities


async def shared_funder(members: list[str], hops: int = 2) -> str | None:
    """Find a wallet that funded ≥60% of members within `hops` (coordination)."""
    driver = get_neo4j()
    async with driver.session() as s:
        result = await s.run(
            f"""
            MATCH (f:Wallet)-[:FUNDED*1..{hops}]->(m:Wallet)
            WHERE m.address IN $members
            WITH f, count(DISTINCT m) AS reached
            WHERE reached >= $threshold
            RETURN f.address AS funder ORDER BY reached DESC LIMIT 1
            """,
            members=members, threshold=max(2, int(0.6 * len(members))),
        )
        rec = await result.single()
        return rec["funder"] if rec else None


def co_buy_lift(observed_pairs: int, possible_pairs: int, baseline_rate: float) -> float:
    """Lift of co-buying vs. a random baseline. >1 means coordinated."""
    if possible_pairs <= 0 or baseline_rate <= 0:
        return 0.0
    observed_rate = observed_pairs / possible_pairs
    return observed_rate / baseline_rate
