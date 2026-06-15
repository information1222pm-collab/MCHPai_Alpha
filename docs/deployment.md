# Deployment

## Local / dev (docker-compose)

```bash
make bootstrap     # .env + build images
make infra-up      # NATS, Postgres, ClickHouse, Neo4j, Redis, MinIO, Prometheus, Grafana, OTel
make migrate       # apply Postgres + ClickHouse + Neo4j schemas
make nats-streams  # create JetStream streams
make up            # start all services
make ps            # health
```

Or one shot: `bash scripts/bootstrap.sh`.

Endpoints (local): API `:8080` · Grafana `:3000` · Prometheus `:9090` ·
Neo4j browser `:7474` · MinIO console `:9001`.

## Configuration

All config is environment-driven (`.env`, typed in
`mchpai_common.config.Settings`). Secrets (`HELIUS_API_KEY`, `YELLOWSTONE_*`,
wallet keypair) are never committed — see `.gitignore` and `WALLET_KEYPAIR_PATH`.

## Production (Kubernetes + Terraform)

* `infrastructure/terraform/` — cloud footprint (compute + data plane +
  observability) as modules; fill in a concrete provider per environment.
* `infrastructure/kubernetes/` — namespace + reference Deployment/HPA. Every
  Python service follows the same shape: stateless pods, JetStream durable
  consumer for horizontal scale, Prometheus scrape annotations, liveness probe.
* `deployments/{local,staging,production}/` — per-environment overlays.

### Topology notes

* **execution-engine**: pin to a low-latency node pool colocated with Yellowstone
  & Jito; usually 1–N replicas sharing the `exec.orders` consumer group.
* **analytics services**: scale horizontally; HPA on CPU/lag.
* **stores**: managed Postgres (HA), ClickHouse (sharded), Neo4j (causal
  cluster), Redis (HA), S3/MinIO.

## Observability

OTLP from every service → `otel-collector` → Tempo (traces) / Prometheus
(metrics) / Loki (logs). Grafana dashboards provisioned from
`infrastructure/grafana/`. Start with the **Platform Overview** dashboard
(events/sec, decision→land latency p50/p99, buy signals, tokens discovered).

## Runbook essentials

* **Pause trading**: `POST /control/pause` (sets `exec:paused`); resume with
  `/control/resume`. Daily-loss-limit auto-pauses.
* **Go live**: set `EXECUTION_MODE=live` and mount the hot wallet keypair; verify
  paper P&L and latency dashboards first.
* **Backfill a new service**: it replays up to 7 days from JetStream on first run.
