# Event Pipeline

Everything flows as events on **NATS JetStream**. This is the platform's nervous
system; services are decoupled producers/consumers.

## Envelope

Every message is an `Envelope` (`libraries/.../events/envelope.py`):

```json
{
  "id": "uuid",
  "type": "WalletBoughtToken",
  "schema_version": "1",
  "occurred_at": "2026-06-03T12:00:00Z",
  "producer": "wallet-ingestion",
  "trace_id": "…",
  "partition_key": "<mint|wallet>",
  "payload": { ... }
}
```

Infra (logging, tracing, replay, DLQ) is generic over the envelope; business code
deserializes `payload` to a typed model via `PAYLOAD_BY_TYPE`.

## Subjects & streams

`mchpai.<domain>.<event>` (`libraries/.../events/subjects.py`). Streams bind to
wildcards:

| Stream            | Subjects               | Events                                   |
|-------------------|------------------------|------------------------------------------|
| `mchpai_TOKENS`   | `mchpai.tokens.>`      | TokenCreated, TokenSnapshot              |
| `mchpai_WALLETS`  | `mchpai.wallets.>`     | WalletCreated/Updated, Bought/Sold       |
| `mchpai_LIQUIDITY`| `mchpai.liquidity.>`   | LiquidityAdded/Removed                   |
| `mchpai_SIGNALS`  | `mchpai.signals.>`     | AttentionSpike, ClusterDetected, Prediction, BuySignal |
| `mchpai_EXEC`     | `mchpai.exec.>`        | TradeExecuted, fills, orders             |

## Core event types

`TokenCreated · TokenSnapshot · WalletCreated · WalletUpdated ·
WalletBoughtToken · WalletSoldToken · LiquidityAdded · LiquidityRemoved ·
AttentionSpike · ClusterDetected · PredictionGenerated · BuySignalGenerated ·
TradeExecuted` (defined in `libraries/.../events/types.py`).

## Delivery semantics

* **Durable consumers + queue groups** → at-least-once, load-balanced across
  replicas. Handlers are idempotent (natural keys + `ON CONFLICT`).
* **`partition_key`** (mint/wallet) preserves per-entity ordering for replay.
* **7-day retention** → new services can backfill by replaying history.
* **NAK with delay** on handler error → automatic retry/backoff.

## The low-latency exception

The hot path (`raw.swaps`, `exec.orders`, `exec.fills`) uses **Redis streams**,
not NATS, to shave the cross-language hop between the Rust engine and Python.
These are operational queues, not the durable event log — the durable record is
re-published to NATS as `WalletBoughtToken`/`TradeExecuted`.

## Adding an event

1. Add a payload model in `events/types.py`.
2. Add a subject constant in `events/subjects.py` and bind it to a stream.
3. Register it in `SUBJECT_BY_TYPE` + `PAYLOAD_BY_TYPE`.

Nothing else changes to *carry* the new event.
