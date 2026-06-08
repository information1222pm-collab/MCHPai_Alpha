# Sources — the reality interface

Reality enters through **one door**. Every source turns observations of the
world into the system's domain events and feeds them to the single source of
truth. The pipeline never varies:

```
Source → Domain Events → Event Log → Replay → wallet_state(t)
```

A source never builds wallet state directly. It only fills the log. This is what
makes a live Helius feed and a year-old archive **interchangeable** inputs to the
exact same intelligence — and what keeps replay deterministic and point-in-time
correct no matter where the data came from.

## Design: pure translation, separable transport

Each source splits into two parts:

* **Translation** — a *pure function* from a provider payload to domain events.
  Fully testable in-process with sample payloads. This is the valuable part, and
  it is verified.
* **Transport** — the thin, lazy adapter that fetches payloads from the network.
  Separable and gated; it carries no intelligence.

This mirrors the persistence layer: the testable core is proven in-sandbox; the
live edge is verified against reality when credentials/endpoints exist.

## The sources

| Source | Role | Status |
|--------|------|--------|
| `ArchiveSource` | **deterministic laboratory** — replay JSONL/Parquet event archives | **Verified**: round-trips to bit-identical `wallet_state(t)`, preserves ingestion time |
| `CSVSource` | raw tabular trade dumps / backfills | **Verified** translation |
| `SyntheticSource` | chaos / fault injection / adversarial testing | **Verified**: deterministic by seed; faults flow through without crashing |
| `HeliusSource` | live Enhanced Transactions | translation **verified vs sample payloads**; transport pending live key |
| `YellowstoneSource` | high-performance Geyser/gRPC | translation **verified vs sample messages**; transport pending live endpoint |
| `RPCSource` | universal JSON-RPC fallback (balance-delta inference) | translation **verified vs sample txns**; transport pending live node |

## ArchiveSource — the laboratory

Most teams skip the archive. It is one of the most valuable pieces here. Capture
any source's output (or an existing log) and replay it forever, identically:

```python
from wis.sources import ArchiveSource, capture, write_jsonl
from wis.app.observatory import Observatory

# capture a live feed once...
write_jsonl(capture(live_observatory.store), "day1.jsonl")

# ...replay it deterministically, any number of times
obs = Observatory()
obs.ingest_source(ArchiveSource("day1.jsonl"))
```

This enables deterministic experiments, regression tests, historical replay,
paper trading, and future simulation — all on a reality you can reproduce.

## The interchangeability guarantee

The proof (`tests/sources/test_interchangeability.py`): the same reality —
*alpha buys GEM, then sells it* — expressed through Helius, Yellowstone, RPC and
CSV reconstructs the **identical** `wallet_state(t)` digest. Provenance (the
`venue` tag) may differ; behavior does not. Sources are interchangeable; only the
door differs.

## Capturing a live feed for replay

Live sources stamp `ingestion_time` at **receipt** (reality has non-deterministic
timing). To make a live feed deterministic, capture its emitted events into an
archive — the archive preserves ingestion time, so the laboratory replays
exactly what the system could have seen, never more.
