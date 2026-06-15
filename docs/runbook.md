# MCHPAI — Operational Runbook (First Light)

> **This document is sacred.** It is the mission manual for bringing the
> observatory online and keeping it observing. Treat changes to it with the same
> rigor as changes to production. When reality and this runbook disagree, fix the
> system or fix the runbook — never ignore the gap.

**Mission phase:** Phase 3 — First Light.
**Mission objective:** Observe mainnet. Record reality with integrity. *No
trading, no models* until the dataset milestones are met.
**Definition of success:** 1 → 10 → 100 → 1,000 token births; 1,000,000
snapshots; 10,000 then 100,000 tokens — all with passing dataset-integrity checks.

---

## 0. Severity & escalation

| Sev | Meaning                                   | Example                               | Response time |
|-----|-------------------------------------------|---------------------------------------|---------------|
| S1  | Observatory blind (no data landing)       | Yellowstone down + no failover        | immediate     |
| S2  | Degraded coverage / data integrity at risk| sustained slot gaps, backpressure full| < 15 min      |
| S3  | Single component impaired, redundancy holds| one RPC endpoint down                 | < 1 h         |
| S4  | Cosmetic / non-data-impacting             | dashboard panel missing               | next day      |

Data-integrity incidents (duplicate births, replay divergence, leakage) are **at
least S2** even if events still flow — corrupt data is worse than no data.

---

## 1. System topology (recap)

Two planes, one bus. See `docs/architecture.md` for detail.

```
 Yellowstone gRPC (failover pool) ──> execution-engine(Rust) ──> Redis raw.swaps
                                                                     │
 wallet-ingestion ─> NATS ─> snapshot-engine ─> ClickHouse snapshots │
        persistence (event_log + births + counters)   state-engine   │
        ground-truth ─> Postgres   feature-engine ─> feat:vec        │
 api-gateway (REST/WS, /stats, /quality)                             │
```

Latency plane = Rust + Redis. Analytical plane = Python + NATS. Stores =
Postgres (truth), ClickHouse (firehose/series), Neo4j (graph), Redis (hot),
MinIO (artifacts).

---

## 2. Infrastructure inventory

| Component     | Purpose                          | Port(s)        | Min resources (prod) |
|---------------|----------------------------------|----------------|----------------------|
| NATS JetStream| event bus                        | 4222, 8222     | 2 vCPU / 4 GB / 20 GB|
| PostgreSQL    | truth DB (births, GT, scores)    | 5432           | 4 vCPU / 16 GB / 200 GB SSD |
| ClickHouse    | firehose + snapshots + states    | 8123, 9000     | 8 vCPU / 32 GB / 1 TB+ SSD |
| Neo4j (+GDS)  | wallet graph                     | 7474, 7687     | 4 vCPU / 16 GB / 200 GB |
| Redis         | hot state + low-latency streams  | 6379           | 2 vCPU / 8 GB        |
| MinIO         | feature/model artifacts          | 9000/9001      | 2 vCPU / 8 GB / 500 GB |
| Prometheus    | metrics                          | 9090           | 2 vCPU / 8 GB        |
| Grafana       | dashboards                       | 3000           | 1 vCPU / 2 GB        |
| OTel collector| traces/logs/metrics fan-out      | 4317/4318      | 1 vCPU / 2 GB        |
| execution-engine (Rust) | ingest + (later) execution | 9100 metrics | 4 vCPU / 8 GB, **colocated** near Yellowstone/Jito |

**External providers:** Helius (RPC + enrichment), a Yellowstone/Geyser provider
(Triton, Helius, etc.), Jito block-engine (execution — *not used in Phase 3*).

---

## 3. Secrets & configuration

Provisioned as environment / mounted secrets — **never committed** (`.gitignore`).

| Secret                | Used by             | Notes                                    |
|-----------------------|---------------------|------------------------------------------|
| `HELIUS_API_KEY`      | token/wallet-ingestion, engine | enrichment + RPC          |
| `YELLOWSTONE_ENDPOINT`| execution-engine    | primary Geyser endpoint                  |
| `YELLOWSTONE_ENDPOINTS`| execution-engine   | comma-separated failover pool (≥2 recommended) |
| `YELLOWSTONE_X_TOKEN` | execution-engine    | provider auth token                      |
| `RPC_1 / RPC_2 / RPC_3` (`SOLANA_RPC_URLS`) | engine | rotation pool for backfill |
| `JITO_AUTH` / `JITO_BLOCK_ENGINE_URL` | engine | **Phase 4 only** — leave unset |
| `POSTGRES_PASSWORD`, `NEO4J_PASSWORD`, `MINIO_SECRET_KEY` | stores | rotate per environment |

**Config validation (pre-flight):** confirm `EXECUTION_MODE=paper`,
`YELLOWSTONE_ENDPOINTS` has ≥1 reachable endpoint, all store URLs resolve, and
clocks are NTP-synced (see §9 time sync).

---

## 4. Pre-flight checklist (go/no-go)

Run before every cold start. **All must be GO.**

- [ ] `.env` present; secrets populated; `EXECUTION_MODE=paper`.
- [ ] Clock synced (NTP); host drift < 250 ms.
- [ ] Datastores reachable (`make infra-up`, healthchecks green).
- [ ] Schemas applied (`make migrate`) — Postgres, ClickHouse, Neo4j.
- [ ] JetStream streams created (`make nats-streams`).
- [ ] MinIO buckets created (`infrastructure/minio/init.sh`).
- [ ] At least one Yellowstone endpoint responds to a test subscribe.
- [ ] Disk headroom: ClickHouse volume < 70% used.
- [ ] Prometheus scraping all targets; Grafana "Platform Overview" loads.

---

## 5. Startup sequence (ordered)

Services have a strict dependency order. Start a tier only when the previous
tier's health gate passes.

```
T0  Infra:        nats, postgres, clickhouse, neo4j, redis, minio
T0+ Observability: prometheus, grafana, otel-collector
T1  Migrate:      make migrate && make nats-streams && minio/init.sh
T2  Persistence:  persistence            (event_log + births must be up FIRST)
T3  Ingestion:    execution-engine (Rust ingest), wallet-ingestion
T4  Time-series:  snapshot-engine
T5  Derivation:   feature-engine, graph-engine, state-engine
T6  Labeling:     ground-truth, creator-intelligence
T7  Surface:      api-gateway, ranking-engine, alert-engine
    (strategy-engine / prediction-engine: PAUSED in Phase 3)
```

Rationale: **persistence starts before ingestion** so the immutable `event_log`
and birth registry capture the very first events — we must never miss a birth.

`make up` brings everything up; for First Light, prefer staged manual starts so
each health gate can be verified.

---

## 6. Health checks & steady-state baselines

Check via Prometheus/Grafana and the API. Baselines are *order-of-magnitude*
expectations for mainnet memecoin hours; calibrate after first 24 h.

| Service          | Healthy signal                                   | Expected rate / budget |
|------------------|--------------------------------------------------|------------------------|
| execution-engine | `mchpai_swaps_ingested_total` rising; slot gaps ≈0| 100s–1000s swaps/s peak |
| wallet-ingestion | `WalletBought/Sold` published; lag→0             | tracks swaps/s         |
| snapshot-engine  | `mchpai_*` snapshots emitted; per-mint seq monotonic | 4 windows × active mints |
| feature-engine   | `feat:vec:{mint}` fresh; compute latency p95      | < 50 ms/snapshot       |
| persistence      | `stats:events` rising; births idempotent          | = total event rate     |
| ground-truth     | labeling cycles complete; `is_final` growing      | every 5 min            |
| Redis            | mem < maxmemory; no evictions on streams          | < 70% maxmemory        |
| ClickHouse       | insert success; parts merging; disk < 70%         | —                      |
| NATS             | no slow consumers; stream bytes bounded           | < 70% max_bytes        |

Quick API checks:
```
curl :8080/healthz          # service alive
curl :8080/stats            # observatory progress (births, snapshots, tokens)
curl :8080/quality          # latest dataset-quality report (see §11)
```

**Latency budget (ingest path):** Yellowstone event → parsed < 15 ms; → on
`raw.swaps` < 25 ms; → snapshot close at window boundary.

---

## 7. Failure modes & responses

For each: **symptoms → automatic behavior → manual recovery.**

### 7.1 RPC outage (Helius / backfill RPC)
- *Symptoms:* enrichment errors; backfill stalls.
- *Automatic:* engine rotates `SOLANA_RPC_URLS`; ingestion continues (enrichment
  is best-effort and cached).
- *Manual:* verify keys/quota; add an endpoint to the rotation; if all down, this
  is **S2** (degraded enrichment, raw ingest may still flow).

### 7.2 Yellowstone disconnect
- *Symptoms:* `swaps_ingested` flatlines on one endpoint; stream error logged.
- *Automatic:* endpoint marked unhealthy → **failover** to next in pool with
  exponential backoff; on reconnect, **slot reconciliation** emits backfill
  requests for missed slots.
- *Manual:* if the whole pool is down → **S1**. Add/replace an endpoint
  (`YELLOWSTONE_ENDPOINTS`), restart engine. Confirm slot gaps close (§7.7).

### 7.3 Redis failure
- *Symptoms:* engine cannot `XADD raw.swaps`; ingest backpressure stalls.
- *Automatic:* engine retries; bounded channel fills → producer slows (no data
  loss for in-flight, but new events drop if Redis stays down). **S1.**
- *Manual:* restore Redis (AOF persistence enabled). On recovery, ingestion
  resumes; missed window covered by slot reconciliation/backfill.

### 7.4 NATS failure
- *Symptoms:* analytical services stop receiving; consumers report disconnect.
- *Automatic:* clients reconnect indefinitely; JetStream is durable so consumers
  **replay from last ack** on recovery — no analytical data lost. **S2.**
- *Manual:* restore NATS; verify streams intact (`nats stream ls`); confirm
  consumer lag drains.

### 7.5 ClickHouse down
- *Symptoms:* snapshot/feature/event_log inserts fail (logged warnings).
- *Automatic:* services keep consuming NATS (durable) but inserts error; on
  recovery they resume. Risk: snapshots computed during outage are lost unless
  re-derivable. **S2.**
- *Manual:* restore ClickHouse; if needed, **rebuild** from the immutable
  `event_log` (see §8.3). Verify snapshot coverage (§11).

### 7.6 Postgres down
- *Symptoms:* births/ground-truth/score writes fail.
- *Automatic:* persistence retries; births re-attempted (idempotent). **S2.**
- *Manual:* restore Postgres (HA/replica). Re-run birth backfill from `event_log`
  `TokenCreated` records — idempotent, safe to replay.

### 7.7 Slot gap
- *Symptoms:* `SlotTracker` reports gaps; `total_gaps` climbs.
- *Automatic:* reconciler emits capped `BackfillRequest`s; backfiller fetches
  missed slots via RPC and replays into `raw.swaps`.
- *Manual:* if gaps persist (backfiller saturated/RPC slow): widen RPC pool,
  raise backfill cap, verify endpoint health. Persistent gaps = **S2**.

### 7.8 Backpressure saturation
- *Symptoms:* ingest bounded channel full; producer awaiting; latency rises.
- *Automatic:* ingestion slows to match the slowest downstream (Redis) — protects
  memory; no OOM.
- *Manual:* find the slow consumer (Redis CPU? ClickHouse merges?); scale it;
  consider raising `INGEST_CHANNEL_CAPACITY` only after fixing the bottleneck.

### 7.9 Disk full (ClickHouse / NATS)
- *Symptoms:* inserts/publishes fail; **S1** risk of data loss.
- *Automatic:* TTLs cap retention (snapshots 180 d, event_log by partition).
- *Manual:* add disk; verify partition TTLs; never delete `event_log` partitions
  that haven't been archived to MinIO.

---

## 8. Recovery procedures

### 8.1 Clean restart
Follow §5 startup order. Persistence first. Verify §6 health gates per tier.

### 8.2 Replay (NATS consumers)
JetStream retains 7 days. A restarted/new consumer replays from its durable
cursor automatically — no action needed beyond restart.

### 8.3 Rebuild derived stores from the event log (source of truth for replay)
The immutable ClickHouse `event_log` is the canonical record. To rebuild
snapshots / states / births after a derived-store loss:
1. Stop the affected derived consumer(s).
2. Replay `event_log` (ordered by `occurred_at`, partitioned by
   `partition_key`) through the same reducers — **deterministic** (see §10).
3. Verify replay determinism + coverage (§11) before resuming live writes.

### 8.4 Birth backfill
Re-run birth recording over `event_log` `TokenCreated` rows. `token_births` is
idempotent (`ON CONFLICT DO NOTHING`), so this is always safe.

---

## 9. Time synchronization

Snapshot windows and sequence ordering depend on consistent time.
- All hosts NTP-synced; alert if drift > 250 ms.
- `block_time` from chain is authoritative for swap timestamps; wall-clock is used
  only for `recorded_at`/quality timing.
- Snapshot `ts` is aligned to window boundaries (5/15/30/60 s) — verify alignment
  in the quality report (§11, "snapshot skew").

---

## 10. Replay determinism (a first-class guarantee)

Reducers (`wallet/creator/graph state`, snapshot aggregation, ground-truth) are
**pure**. Given the same ordered events they produce identical output. This is
verified by unit tests (`tests/unit/test_quality.py::replay`) and should be
re-verified on a sample after any reducer change. If replay diverges, **stop
ingestion (S2)** and bisect the change — non-deterministic derivation poisons
every downstream dataset and model.

---

## 11. Dataset integrity & quality (run continuously)

Empirical science: *does reality agree?* Run `scripts/validate_dataset.py` (cron,
e.g. every 15 min). It writes a report to Redis `quality:report`, surfaced at
`GET /quality`. See `docs/dataset_validation.md` for the full checklist. Headline
checks:

- **Event completeness** — `event_log` count vs. expected from slot coverage.
- **Slot gaps** — total/maximum gaps; backfill backlog.
- **Duplicate births** — must be **0** (registry is idempotent).
- **Snapshot coverage / skew** — per-(mint,window) seq monotonic; ts on boundary.
- **Feature null rates** — per-feature share of zeros/nulls.
- **Label maturity** — fraction of `ground_truth.is_final`.
- **Replay determinism** — sample reducer replay matches stored state.
- **Online/offline consistency** — live `feat:vec` vs. recomputed offline vector.
- **Feature drift / distribution shift** — PSI vs. a reference window.

A **GREEN** report is required before advancing milestones or (later) training.

---

## 12. Shutdown

1. Pause discovery sources (optional) to quiesce new births.
2. `docker compose stop` analytical tier (T7→T3) — JetStream retains state.
3. Flush snapshot-engine in-flight buckets (idle flush handles this).
4. Stop ingestion (execution-engine).
5. Stop persistence **last** (so it logs the tail of events).
6. Stop infra. Volumes persist; nothing authoritative lives only in memory.

---

## 13. Change management

- The runbook changes via PR with the same review bar as code.
- Any new failure mode discovered in ops gets a §7 entry **the same day**.
- Reducer/schema changes require a replay-determinism re-verification (§10).
- Phase gates (First Light → Million Snapshot → training) are explicit go/no-go
  decisions recorded against the criteria in `docs/first_light.md`.

---

## 14. Command cheat-sheet

```
make bootstrap            # .env + build
make infra-up             # datastores + bus + observability
make migrate              # schemas (pg + clickhouse + neo4j)
make nats-streams         # JetStream streams
make up / make ps         # start all / status
make logs S=snapshot-engine

curl :8080/stats          # observatory progress
curl :8080/quality        # dataset-quality report
python scripts/first_light.py        # milestone status
python scripts/validate_dataset.py   # run integrity checks → Redis + stdout
```
