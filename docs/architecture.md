# Architecture

MCHPAI is an **event-driven, domain-driven** quantitative intelligence platform.
This document is the map; the sibling docs drill into each area.

## Layers

```
            ┌─────────────────────────── plugin / UI ───────────────────────────┐
            │                     api-gateway (REST + WS)                         │
            └───────────────▲───────────────────────────────▲────────────────────┘
                            │ reads                          │ controls
   ┌────────────────────────┴───────────────────────────────┴───────────────────┐
   │                              SERVICES (bounded contexts)                     │
   │  token-ingestion  wallet-ingestion  feature-engine  graph-engine            │
   │  prediction-engine  strategy-engine  execution-engine(Rust)                 │
   │  ranking-engine  alert-engine                                               │
   └───────▲───────────────────────────────────────────────────────────▲────────┘
           │ publish/subscribe (NATS JetStream)                          │
   ┌───────┴─────────────────────────────────────────────────────────────────────┐
   │                               EVENT BUS (NATS)                                │
   │  mchpai.tokens.>  mchpai.wallets.>  mchpai.liquidity.>  mchpai.signals.>      │
   │  mchpai.exec.>                                                                │
   └───────▲───────────────────────────────────────────────────────────▲─────────┘
           │                                                             │
   ┌───────┴───────────┐  ┌────────────┐  ┌──────────┐  ┌─────────┐  ┌──┴───────┐
   │   PostgreSQL      │  │ ClickHouse │  │  Neo4j   │  │  Redis  │  │  MinIO   │
   │  truth database   │  │ time-series│  │  graph   │  │  cache  │  │ features │
   └───────────────────┘  └────────────┘  └──────────┘  └─────────┘  │ + models │
                                                                      └──────────┘
```

## Two planes

* **Analytical plane** (Python, NATS): high throughput, model iteration, scales
  horizontally via JetStream consumer groups.
* **Latency plane** (Rust, Redis): the hot path — Geyser ingest and Jito
  execution — where tail latency is the product.

The seam between them is Redis streams (`raw.swaps`, `exec.orders`, `exec.fills`),
chosen for the lowest possible cross-language hop on the critical path.

## Bounded contexts

Each service owns one context and one piece of the pipeline; they share *only*
versioned schemas (`libraries/mchpai_common/schemas`) and events
(`.../events`). No service imports another service. This is what lets the system
grow to 100+ services without a tangle.

## Design rules

1. Communicate via events, never direct calls.
2. Schemas are forward-compatible; bump `SCHEMA_VERSION` on breaks.
3. Stateless services; all state in the data plane.
4. Observability is mandatory (metrics + traces + logs from day one).
5. Research (`research/`, `notebooks/`) is isolated from production (`services/`).

See: [system_overview](system_overview.md) · [event_pipeline](event_pipeline.md)
· [database_design](database_design.md).
