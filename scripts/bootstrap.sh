#!/usr/bin/env bash
# One-shot local bootstrap: env, infra, schemas, streams.
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || cp .env.example .env
echo ">> infra up"
docker compose up -d nats postgres clickhouse neo4j redis minio prometheus grafana otel-collector

echo ">> waiting for postgres"
until docker compose exec -T postgres pg_isready -U mchpai >/dev/null 2>&1; do sleep 1; done

echo ">> schemas"
docker compose exec -T postgres psql -U mchpai -d mchpai < infrastructure/postgres/init.sql
docker compose exec -T clickhouse clickhouse-client --multiquery < infrastructure/clickhouse/init.sql || true
cat infrastructure/neo4j/init.cypher | docker compose exec -T neo4j cypher-shell -u neo4j -p mchpai_dev_pw || true

echo ">> minio buckets"
bash infrastructure/minio/init.sh || true

echo ">> nats streams"
bash scripts/create_streams.sh || true

echo "Bootstrap complete. Run: docker compose up -d  (to start services)"
