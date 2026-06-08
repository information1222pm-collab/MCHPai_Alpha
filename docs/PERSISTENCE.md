# Persistence & the correctness oracle

Connecting the observatory to reality means writing the event log and its
derived views to durable stores — *without* surrendering the two sacred
invariants: **replay determinism** and **point-in-time correctness**. The
strategy is a single, ruthless idea:

> The in-memory implementation is the **oracle**. An adapter is correct if and
> only if, given the same log, it reproduces **bit-identical** state.

Nothing is called "verified" until it has passed this check against a live
service.

## How correctness is enforced

* **The codec** (`wis.eventsourcing.codec`) serializes every event losslessly
  and deterministically (`decode(encode(e)) == e`, canonical bytes). Verified
  in-process.
* **World digests** (`wis.conformance`) fingerprint a projected
  `wallet_state(t)` / `graph(t)` exactly — money rendered as rationals, so two
  worlds are compared for *true* equality, not approximate equality.
* **`assert_eventstore_conforms`** drives an adapter and the oracle with the same
  canonical log and asserts identical sequencing, ordering, point-in-time reads,
  round-trip fidelity, and — the sacred one — identical replay digests.
* **`projection_rows`** maps a projected world to exact, ordered storage rows
  with *no database dependency*, so the projection→sink mapping is verified
  in-process and the DB adapters stay thin.

## Roles & verification status

| Store | Adapter | Role | Status |
|-------|---------|------|--------|
| (embedded) | `SqliteEventStore` | durable event log | **Verified in-sandbox** — passes conformance and replays bit-identically from disk after restart |
| PostgreSQL | `PostgresEventStore` | system-of-record event log | Implemented; gated conformance test (`WIS_PG_DSN`) |
| NATS JetStream | `JetStreamEventStore` | event backbone | Implemented; gated conformance test (`WIS_NATS_URL`) |
| MinIO | `MinioReplayArchive` | replay-log archive | Implemented; gated restore-replay test (`WIS_MINIO_ENDPOINT`) |
| Redis | `RedisStateStore` | hot `wallet_state(t)` view | Implemented; gated read-back test (`WIS_REDIS_URL`) |
| ClickHouse | `ClickHouseTradeSink` | analytical trade table | Implemented; gated exact-pnl test (`WIS_CLICKHOUSE_HOST`) |
| Neo4j | `Neo4jGraphSink` | relationship graph | Implemented; gated edge round-trip test (`WIS_NEO4J_URI`) |

The mapping layer feeding the derived sinks (`projection_rows`) is itself
verified in-sandbox against the oracle.

## Running live conformance

```bash
docker compose -f deploy/docker-compose.yml up -d
WIS_PG_DSN=postgresql://wis:wis@localhost:5432/wis \
WIS_REDIS_URL=redis://localhost:6379/0 \
WIS_NATS_URL=nats://localhost:4222 \
WIS_CLICKHOUSE_HOST=localhost \
WIS_NEO4J_URI=bolt://localhost:7687 \
WIS_MINIO_ENDPOINT=localhost:9000 \
make test-integration
```

Adapters with no configured service **skip** (they never fail the suite), so the
gate is honest: green means *actually verified against reality*, not merely
"implemented".

## A note on honesty

Event ids are a pure function of `(sequence, payload)`, so stores either persist
them or recompute them on read — either way they match the oracle. Money is
never rounded in the thing of record: rationals are the source of truth;
floats appear only as analytical conveniences alongside them. Performance work
(batching, async paths, a Rust hot loop) comes *after* correctness, behind this
same verified contract — never before it.
