#!/usr/bin/env bash
# Create MinIO buckets for the feature store and model artifact registry.
# Run after `make infra-up`. Idempotent.
set -euo pipefail

ENDPOINT="${MINIO_ENDPOINT:-http://localhost:9002}"
ACCESS="${MINIO_ACCESS_KEY:-mchpai}"
SECRET="${MINIO_SECRET_KEY:-mchpai_dev_secret}"

mc alias set mchpai "${ENDPOINT}" "${ACCESS}" "${SECRET}"

for bucket in features models datasets backtests; do
  mc mb --ignore-existing "mchpai/${bucket}"
  mc version enable "mchpai/${bucket}" || true
done

echo "MinIO buckets ready: features, models, datasets, backtests"
