<div align="center">

# 🛰️ MCHPAI — Quantitative Intelligence Platform for Solana

**An intelligence platform, not a trading bot.**

Inspired by the architectures of Palantir, Renaissance Technologies, Jane Street,
Citadel, and NASA mission control — designed for *decades* of growth.

</div>

---

MCHPAI is an event-driven, horizontally-scalable platform for discovering,
modeling, and acting on Solana memecoin and wallet intelligence. It treats the
on-chain world as a living system to be *measured* — borrowing first-class ideas
from **epidemiology** (how tokens spread), **ecology** (predator/prey wallet
dynamics), **astronomy** (gravity/attention models), **entropy theory**
(information flow), and the **battlefield** (situational awareness, OODA loops).

The platform is built to eventually support:

- **100+ microservices**
- **1,000+ engineered features**
- **100,000+ active tokens**
- **millions of wallets**
- **graph neural networks, transformers, reinforcement learning, multi-agent systems**

> Architecture is the product. A poor architecture can cripple a brilliant model;
> a brilliant architecture can support generations of models we haven't imagined yet.

---

## Design principles

1. **Event-driven** — services communicate only through events on **NATS
   JetStream**. Never tightly coupled.
2. **Domain-driven** — bounded contexts (`token`, `wallet`, `graph`, `feature`,
   `prediction`, `execution`) with shared, versioned **schemas** as the contract.
3. **Extensibility over simplicity** — every subsystem is a plug-in point.
4. **Observability everywhere** — metrics (Prometheus), traces (Tempo/Jaeger),
   logs (Loki) on every service from day one.
5. **Research / production separation** — `research/` is allowed to be chaotic;
   `services/` must stay stable.
6. **Horizontal scalability** — stateless services + consumer groups + sharded
   stores.

---

## Monorepo layout

```
mchpai/
├── docs/             # Living design docs (architecture, pipelines, ML, ...)
├── infrastructure/   # Docker, Terraform, K8s, datastores, NATS, observability
├── services/         # Independent, event-driven microservices
├── libraries/        # Shared code: schemas, events, db, domain sciences
├── models/           # Trainable models (xgb/lgbm/catboost/gnn/transformers/rl)
├── monitoring/       # Prometheus, Grafana, Tempo, Loki, Jaeger, OTel collector
├── notebooks/        # Research sandbox (analysis & experiments)
├── research/         # Chaotic R&D: entropy, epidemiology, game theory, ecology…
├── tests/            # unit / integration / load
├── scripts/          # Bootstrap & ops scripts
├── deployments/      # Per-environment deployment overlays
├── docker-compose.yml
├── .env.example
└── Makefile
```

## The services (bounded contexts)

| Service              | Lang   | Responsibility                                            |
|----------------------|--------|-----------------------------------------------------------|
| `token-ingestion`    | Python | Pump.fun/Raydium/Meteora/Birdeye/Jupiter/Helius/Yellowstone → `TokenCreated`, `TokenSnapshot` |
| `wallet-ingestion`   | Python | Transactions → `WalletActivity`, `WalletBoughtToken`, …   |
| `feature-engine`     | Python | Creator/liquidity/entropy/spread/attention features       |
| `graph-engine`       | Python | Wallet / funding / token / cluster graphs (Neo4j)         |
| `prediction-engine`  | Python | XGBoost/LightGBM/CatBoost → (GNN/Transformers) predictions|
| `execution-engine`   | Rust   | Jito + QUIC + Yellowstone + RPC rotation, lowest latency  |
| `strategy-engine`    | Python | Position sizing, portfolio logic                          |
| `ranking-engine`     | Python | Live leaderboards                                         |
| `alert-engine`       | Python | Discord / Telegram / Email / Webhooks                     |
| `api-gateway`        | Python | FastAPI REST + WebSocket surface                          |

## The data plane

| Store        | Role                                            |
|--------------|-------------------------------------------------|
| **PostgreSQL** | Truth database (entities, positions, fills)   |
| **ClickHouse** | Time-series & analytics (snapshots, features) |
| **Neo4j**      | Graph intelligence (wallets, funding, clusters)|
| **Redis**      | Hot cache & low-latency state                  |
| **MinIO**      | Feature store & model artifact storage (S3)   |
| **NATS JetStream** | Event bus / durable streams               |

## The exotic libraries (first-class citizens)

`libraries/` includes domains most trading systems ignore — here they are core:

- **entropy** — information content & surprise of token/wallet flows
- **epidemiology** — SIR-style contagion models of how tokens "infect" wallets
- **ecology** — predator/prey, carrying capacity, niche competition of wallets
- **astronomy** — gravity/attention models, "mass" and orbital pull of tokens
- **battlefield** — OODA-loop situational awareness, threat & kill-chain framing
- **forecasting** — generic time-series & survival forecasting toolkit

---

## Core event types

`TokenCreated · TokenSnapshot · WalletCreated · WalletUpdated ·
WalletBoughtToken · WalletSoldToken · LiquidityAdded · LiquidityRemoved ·
AttentionSpike · ClusterDetected · PredictionGenerated · BuySignalGenerated ·
TradeExecuted`

See [`docs/event_pipeline.md`](docs/event_pipeline.md) and
[`libraries/mchpai_common/mchpai_common/events`](libraries/mchpai_common/mchpai_common/events).

---

## Quick start

```bash
make bootstrap        # copy .env, build images
make infra-up         # NATS, Postgres, ClickHouse, Neo4j, Redis, MinIO, observability
make migrate          # apply schemas
make up               # start all services
make ps               # health
```

See [`docs/deployment.md`](docs/deployment.md) for details.

> ⚠️ Research/automation tooling for on-chain data. Not financial advice.
