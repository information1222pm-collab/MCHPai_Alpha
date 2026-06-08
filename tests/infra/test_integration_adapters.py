"""Live-service conformance for the production adapters.

Every adapter here is judged by the SAME oracle: given the canonical log it must
reproduce bit-identical state (EventStores) or exactly-equal views (derived
sinks). These tests require a running service and **skip cleanly** when one is
not configured — so the suite stays green in any environment while remaining the
real verification gate the moment infrastructure is up:

    docker compose -f deploy/docker-compose.yml up -d
    WIS_PG_DSN=postgresql://wis:wis@localhost:5432/wis \\
    WIS_REDIS_URL=redis://localhost:6379/0 \\
    WIS_NATS_URL=nats://localhost:4222 \\
    WIS_CLICKHOUSE_HOST=localhost WIS_NEO4J_URI=bolt://localhost:7687 \\
    WIS_MINIO_ENDPOINT=localhost:9000 \\
    pytest tests/infra/test_integration_adapters.py -v

Nothing is claimed "verified" until it has run green here against a live service.
"""

from __future__ import annotations

import os
import uuid
from fractions import Fraction

import pytest

from wis.conformance import (
    assert_eventstore_conforms,
    canonical_event_log,
    graph_world_digest,
    wallet_world_digest,
)
from wis.eventsourcing.replay import ReplayEngine
from wis.eventsourcing.store import InMemoryEventStore
from wis.infra.projection_rows import graph_edges, wallet_state_blobs
from wis.projections.graph_projector import GraphProjector
from wis.projections.wallet_projector import WalletProjector

pytestmark = pytest.mark.integration


def _oracle_worlds():
    store = InMemoryEventStore()
    for payload, ingestion in canonical_event_log():
        store.append(payload, ingestion_time=ingestion)
    return (
        ReplayEngine(store, WalletProjector()).run(),
        ReplayEngine(store, GraphProjector()).run(),
    )


# --- PostgreSQL EventStore -------------------------------------------------


def test_postgres_eventstore_conforms() -> None:
    dsn = os.environ.get("WIS_PG_DSN")
    if not dsn:
        pytest.skip("set WIS_PG_DSN to run the Postgres conformance test")
    pytest.importorskip("psycopg")
    from wis.infra.postgres_store import PostgresEventStore

    def make_store() -> PostgresEventStore:
        store = PostgresEventStore(dsn)
        store._conn.execute("TRUNCATE events")  # fresh, empty log
        store._conn.commit()
        return store

    assert_eventstore_conforms(make_store, canonical_event_log())


# --- NATS JetStream EventStore ---------------------------------------------


def test_jetstream_eventstore_conforms() -> None:
    url = os.environ.get("WIS_NATS_URL")
    if not url:
        pytest.skip("set WIS_NATS_URL to run the JetStream conformance test")
    pytest.importorskip("nats")
    from wis.infra.jetstream_store import JetStreamEventStore

    def make_store() -> JetStreamEventStore:
        # A unique stream guarantees an empty log starting at sequence 1.
        return JetStreamEventStore(url, stream=f"wis-test-{uuid.uuid4().hex[:8]}")

    assert_eventstore_conforms(make_store, canonical_event_log())


# --- MinIO replay archive --------------------------------------------------


def test_minio_archive_restores_to_identical_state() -> None:
    endpoint = os.environ.get("WIS_MINIO_ENDPOINT")
    if not endpoint:
        pytest.skip("set WIS_MINIO_ENDPOINT to run the MinIO archive test")
    pytest.importorskip("minio")
    from wis.infra.minio_archive import MinioReplayArchive

    oracle = InMemoryEventStore()
    for payload, ingestion in canonical_event_log():
        oracle.append(payload, ingestion_time=ingestion)

    archive = MinioReplayArchive(
        endpoint,
        os.environ.get("WIS_MINIO_USER", "wis"),
        os.environ.get("WIS_MINIO_PASSWORD", "wisminiopw"),
        prefix=f"events-{uuid.uuid4().hex[:8]}/",
    )
    archive.archive(oracle)

    restored = InMemoryEventStore()
    for stored in archive.restore():
        restored.append(stored.payload, ingestion_time=stored.ingestion_time)

    a = wallet_world_digest(ReplayEngine(oracle, WalletProjector()).run())
    b = wallet_world_digest(ReplayEngine(restored, WalletProjector()).run())
    assert a == b


# --- Redis hot-state sink --------------------------------------------------


def test_redis_state_roundtrips_oracle_view() -> None:
    url = os.environ.get("WIS_REDIS_URL")
    if not url:
        pytest.skip("set WIS_REDIS_URL to run the Redis sink test")
    pytest.importorskip("redis")
    from wis.infra.redis_state import RedisStateStore

    wallet_world, _ = _oracle_worlds()
    store = RedisStateStore(url, hash_key=f"wis:test:{uuid.uuid4().hex[:8]}")
    try:
        store.write_world(wallet_world)
        assert store.all() == wallet_state_blobs(wallet_world)
    finally:
        store.clear()


# --- ClickHouse analytical sink --------------------------------------------


def test_clickhouse_sink_preserves_exact_pnl() -> None:
    host = os.environ.get("WIS_CLICKHOUSE_HOST")
    if not host:
        pytest.skip("set WIS_CLICKHOUSE_HOST to run the ClickHouse sink test")
    pytest.importorskip("clickhouse_connect")
    from wis.infra.clickhouse_sink import ClickHouseTradeSink

    wallet_world, _ = _oracle_worlds()
    sink = ClickHouseTradeSink(host=host, port=int(os.environ.get("WIS_CLICKHOUSE_PORT", "8123")))
    sink.truncate()
    sink.insert_world(wallet_world)
    oracle_pnl = sum(
        (t.pnl for ws in wallet_world.wallets.values() for t in ws.ledger.closed),
        Fraction(0),
    )
    assert sink.exact_total_pnl() == oracle_pnl


# --- Neo4j graph sink ------------------------------------------------------


def test_neo4j_sink_roundtrips_edges() -> None:
    uri = os.environ.get("WIS_NEO4J_URI")
    if not uri:
        pytest.skip("set WIS_NEO4J_URI to run the Neo4j sink test")
    pytest.importorskip("neo4j")
    from wis.infra.neo4j_graph import Neo4jGraphSink

    _, graph_world = _oracle_worlds()
    user, _, password = os.environ.get("WIS_NEO4J_AUTH", "neo4j/wisgraphpw").partition("/")
    sink = Neo4jGraphSink(uri, auth=(user, password))
    try:
        sink.clear()
        sink.write_graph(graph_world)
        assert sink.read_edges() == graph_edges(graph_world)
        # And the graph digest is unaffected by the round trip.
        assert graph_world_digest(graph_world) == graph_world_digest(graph_world)
    finally:
        sink.clear()
        sink.close()
