"""Neo4j write/query helpers for the wallet graph."""

from __future__ import annotations

from mchpai_common.database import get_neo4j


async def upsert_bought(wallet: str, mint: str, sol: float, ts) -> None:
    driver = get_neo4j()
    async with driver.session() as s:
        await s.run(
            """
            MERGE (w:Wallet {address:$wallet})
            MERGE (t:Token {mint:$mint})
            MERGE (w)-[b:BOUGHT {ts:$ts}]->(t)
              ON CREATE SET b.sol = $sol
            """,
            wallet=wallet, mint=mint, sol=sol, ts=ts,
        )


async def upsert_funding(funder: str, fundee: str, sol: float, ts) -> None:
    driver = get_neo4j()
    async with driver.session() as s:
        await s.run(
            """
            MERGE (a:Wallet {address:$funder})
            MERGE (b:Wallet {address:$fundee})
            MERGE (a)-[f:FUNDED]->(b)
              ON CREATE SET f.sol=$sol, f.ts=$ts
            """,
            funder=funder, fundee=fundee, sol=sol, ts=ts,
        )


async def link_co_buyers(mint: str, window_seconds: int = 120) -> int:
    """Create CO_BOUGHT edges between wallets that bought the same mint within Δt."""
    driver = get_neo4j()
    async with driver.session() as s:
        result = await s.run(
            """
            MATCH (a:Wallet)-[ba:BOUGHT]->(t:Token {mint:$mint})<-[bb:BOUGHT]-(b:Wallet)
            WHERE a.address < b.address
              AND abs(ba.ts - bb.ts) <= $w
            MERGE (a)-[c:CO_BOUGHT {mint:$mint}]->(b)
              ON CREATE SET c.dt_seconds = abs(ba.ts - bb.ts)
            RETURN count(*) AS n
            """,
            mint=mint, w=window_seconds,
        )
        rec = await result.single()
        return int(rec["n"]) if rec else 0
