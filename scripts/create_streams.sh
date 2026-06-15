#!/usr/bin/env bash
# Create the NATS JetStream streams the platform publishes to.
# Idempotent: `nats stream add` with --defaults updates if it already exists.
# Requires the `nats` CLI (https://github.com/nats-io/natscli).
set -euo pipefail

NATS_URL="${NATS_URL:-nats://localhost:4222}"
P="mchpai"

declare -A STREAMS=(
  [TOKENS]="${P}.tokens.>"
  [WALLETS]="${P}.wallets.>"
  [LIQUIDITY]="${P}.liquidity.>"
  [SIGNALS]="${P}.signals.>"
  [EXEC]="${P}.exec.>"
)

for name in "${!STREAMS[@]}"; do
  subj="${STREAMS[$name]}"
  echo ">> ensuring stream ${P}_${name} (${subj})"
  nats --server "$NATS_URL" stream add "${P}_${name}" \
    --subjects "$subj" \
    --storage file \
    --retention limits \
    --max-age 7d \
    --max-bytes 20GB \
    --replicas 1 \
    --discard old \
    --dupe-window 2m \
    --defaults 2>/dev/null || \
  nats --server "$NATS_URL" stream edit "${P}_${name}" --subjects "$subj" --force 2>/dev/null || true
done

echo "JetStream streams ready."
