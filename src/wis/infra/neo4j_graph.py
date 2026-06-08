"""Neo4j — the persistent wallet relationship graph.

Neo4j holds ``graph(t)`` at scale: wallets as nodes, funding lineage and co-buy
coordination as relationships. It is a derived store whose edges are a pure
function of the projected graph (:func:`graph_edges`); reproducing identical
results means the edges read back equal the oracle's edge set exactly.

The neo4j driver is imported lazily.
"""

from __future__ import annotations

from wis.infra.projection_rows import Edge, graph_edges
from wis.projections.graph_projector import GraphWorld


class Neo4jGraphSink:
    def __init__(self, uri: str, auth: tuple[str, str], *, database: str = "neo4j") -> None:
        from neo4j import GraphDatabase  # lazy

        self._driver = GraphDatabase.driver(uri, auth=auth)
        self._database = database

    def write_graph(self, world: GraphWorld) -> int:
        edges = graph_edges(world)
        with self._driver.session(database=self._database) as session:
            for w in sorted(n.value for n in world.graph.nodes):
                session.run("MERGE (:Wallet {address: $a})", a=w)
            for e in edges:
                # Relationship type cannot be parameterized, so branch on kind.
                rel = "FUNDED" if e.kind == "FUNDED" else "COBUY"
                session.run(
                    f"""
                    MATCH (s:Wallet {{address: $s}})
                    MATCH (t:Wallet {{address: $t}})
                    MERGE (s)-[r:{rel}]->(t)
                    SET r.weight = $w
                    """,
                    s=e.source, t=e.target, w=e.weight,
                )
        return len(edges)

    def read_edges(self) -> list[Edge]:
        edges: list[Edge] = []
        with self._driver.session(database=self._database) as session:
            result = session.run(
                """
                MATCH (s:Wallet)-[r]->(t:Wallet)
                RETURN s.address AS source, t.address AS target, type(r) AS kind, r.weight AS weight
                """
            )
            for rec in result:
                edges.append(
                    Edge(source=rec["source"], target=rec["target"], kind=rec["kind"], weight=float(rec["weight"]))
                )
        edges.sort(key=lambda e: (e.kind, e.source, e.target))
        return edges

    def clear(self) -> None:
        with self._driver.session(database=self._database) as session:
            session.run("MATCH (n:Wallet) DETACH DELETE n")

    def close(self) -> None:
        self._driver.close()
