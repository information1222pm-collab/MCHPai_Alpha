# MCHPAI — Advanced Wallet Intelligence System

> Prices are effects. Participants are causes.
>
> This is not a copy-trading bot. It is a quantitative **intelligence platform**
> that understands the quality, behavior, relationships, and evolution of market
> participants. Build the observatory first; prediction and execution emerge
> later.

The system treats wallets as **evolving entities, not static addresses** — every
wallet is a movie, indexed by time as `wallet_state(t)`. Its mission is to
transform anonymous addresses into understandable entities:

```
transactions → behavior → intelligence → (eventually) foresight
```

It is designed in the spirit of Palantir Foundry, Renaissance Technologies, Jane
Street, the Bloomberg Terminal, NASA Mission Control, and intelligence-agency
architectures — and built for decades of growth.

---

## What exists today

A genuinely runnable, fully-tested **vertical slice of the core architecture**.
The intelligence core has **zero third-party runtime dependencies** and is
deterministic end-to-end:

```
event log → event store → deterministic replay → wallet_state(t)
          → feature factory → truth-weighted scoring
          → graph(t) → Louvain clusters → research labs → read-only API
```

See it in 5 seconds (no infrastructure required):

```bash
uv venv && source .venv/bin/activate
uv pip install -e .            # core only; no heavy deps
PYTHONPATH=src python -m wis.app.demo
```

You'll watch a wallet's **alpha rise as confidence accrues** (the movie), see its
**DNA** named with evidence, and see **communities** emerge from co-buying.

---

## Architecture at a glance

| Layer | Package | Responsibility |
|------|---------|----------------|
| **Domain** | `wis.domain` | Pure model: time/sequence, money, events, `wallet_state(t)`, metrics, DNA, `graph(t)`, Louvain |
| **Event sourcing** | `wis.eventsourcing` | Append-only log, stored-event envelope, **deterministic replay** |
| **Projections** | `wis.projections` | Pure folds: events → `wallet_state(t)` and `graph(t)` |
| **Feature factory** | `wis.features` | Declarative `FeatureSpec` + `FeatureCompiler`: point-in-time, leak-free, versioned, online/offline-consistent |
| **Scoring** | `wis.scoring` | `wallet_alpha_score` and components — **optimized for truth, not profitability**, with confidence shrinkage |
| **Graph intelligence** | `wis.domain.graph` | Funding trees, co-buy graph, communities, centrality/influence |
| **Research** | `wis.research` | Seven labs. **No execution. No copy trading. No position sizing.** |
| **Application** | `wis.app` | `Observatory` facade + read-only FastAPI surface |
| **Infrastructure** | `wis.infra` | Adapter contracts + config for Postgres / ClickHouse / Redis / Neo4j / NATS / MinIO |

Two invariants hold the whole thing together:

1. **Replay determinism.** Given the same ordered log, every projection produces
   bit-identical state — today and in ten years. Money is exact rationals; there
   is no wall-clock or RNG inside a fold.
2. **Point-in-time correctness.** A feature computed *as of* `T` can only read
   facts ingested by `T`. Look-ahead leakage is structurally impossible, not
   merely discouraged.

Read more in [`ARCHITECTURE.md`](ARCHITECTURE.md), [`docs/PHILOSOPHY.md`](docs/PHILOSOPHY.md),
[`docs/EVENTS.md`](docs/EVENTS.md), and [`docs/ROADMAP.md`](docs/ROADMAP.md).

---

## Core concepts

**`wallet_state(t)` — wallets are movies.** Every wallet carries performance,
timing, conviction, risk and intelligence metrics derived from an exact FIFO
trade ledger. Pin two frames and watch the wallet evolve.

**Wallet DNA.** A qualitative, *explainable* profile — strengths, weaknesses,
tendencies — where every trait is backed by a metric and a threshold.

**Truth over hype.** Scores live in `[0,1]` and answer "how strongly does the
evidence support this quality?" A wallet with two lucky trades is shrunk toward
neutral; certainty grows only with observation. Metrics that need data we have
not ingested (rug exposure, etc.) report `None` — honest absence over fiction.

**`graph(t)` — clusters are movies too.** Funding lineage and temporal co-buy
edges form a graph; communities emerge via deterministic Louvain and evolve over
time.

---

## Persistence & the correctness oracle

Connecting the observatory to reality must not cost us determinism. The
in-memory store is the **oracle**: an adapter is correct iff, given the same log,
it reproduces **bit-identical** state. A lossless event **codec**, exact
**world-digest** fingerprints, and a store-agnostic **conformance harness**
(`wis.conformance`) enforce this.

The durable **SQLite** EventStore is *verified in-sandbox* — it passes
conformance and replays bit-identically from disk after a restart. Adapters for
**PostgreSQL**, **NATS JetStream + MinIO**, **Redis**, **ClickHouse** and
**Neo4j** are implemented and wired to the same harness via integration-gated
tests that turn green the moment a live service is up. Details and verification
status: [`docs/PERSISTENCE.md`](docs/PERSISTENCE.md).

```bash
make infra-up        # docker compose: postgres, clickhouse, redis, neo4j, nats, minio
make test-integration  # runs the conformance harness against whatever is configured
```

---

## Sources — reality enters through one door

Every source — historical archive, Helius, Yellowstone, RPC, CSV, synthetic —
turns observations into the **same domain events** and feeds the log. Sources are
interchangeable; only the door differs.

```
Source → Domain Events → Event Log → Replay → wallet_state(t)
```

`ArchiveSource` is the **deterministic laboratory**: capture any feed and replay
it forever to bit-identical state — the basis for regression tests, paper
trading and simulation. Live sources split into a *verified pure translator* and
a *gated network transport*. The crown property is proven: Helius, Yellowstone,
RPC and CSV all reconstruct the identical `wallet_state(t)`. Details:
[`docs/SOURCES.md`](docs/SOURCES.md).

```python
from wis.app.observatory import Observatory
from wis.sources import ArchiveSource

obs = Observatory()
obs.ingest_source(ArchiveSource("day1.jsonl"))   # one door, any source
```

---

## Development

```bash
uv venv && source .venv/bin/activate
uv pip install -e '.[dev]'
pytest -q                       # pure-Python, no services needed
ruff check src tests
```

Run the deployed infrastructure (for the scale-out adapters):

```bash
docker compose -f deploy/docker-compose.yml up -d
```

Serve the read-only observatory API:

```bash
uv pip install -e '.[api]'
uvicorn 'wis.app.api.server:create_app' --factory
```

---

## What this is **not**

By charter, and on purpose: no execution, no copy trading, no Jito/bundling, no
position sizing, no trading decisions. This phase exists solely to *understand*
wallets. The observatory comes first.
