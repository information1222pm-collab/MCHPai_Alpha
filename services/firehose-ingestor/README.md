# firehose-ingestor — full-coverage server-side Alpha engine

The dashboard (`observation.html`) runs its Alpha engine on a **browser poll
sample** of the chain. This service runs the **same intelligence server-side**
against the **complete DEX firehose**, so the wallet grading, Alpha Score, and
signal feed see *every* swap on the watched programs — not a slice.

```
firehose (transport)  ─►  AlphaEngine (port of the dashboard brain)  ─►  FastAPI
   MockFirehose                 wallet grading                            /signals
   HeliusWsFirehose             composite Alpha Score                     /alpha
   YellowstoneFirehose(stub)    7 signal detectors                        WS /stream
```

## Why this is the big lever
In the browser, coverage is capped by what one tab can poll. Server-side, a
single WebSocket subscription to the DEX programs delivers the whole stream, so
the Alpha Score is computed over real population statistics and wallet grades
converge far faster. Point the dashboard at this service's `/stream` and it
plots/decides on full-coverage data with **zero browser API usage**.

## Run it

```bash
pip install -r services/firehose-ingestor/requirements.txt
pip install -e libraries/mchpai_common          # engine/parser

# real firehose (Helius standard plan is enough for the WebSocket path):
HELIUS_API_KEY=xxxx PORT=8787 \
  python -m firehose_ingestor            # run from services/firehose-ingestor/

# no key? it serves a synthetic demo stream so you can poke the API:
python -m firehose_ingestor
```

Optional env: `FOLLOWS_FILE` (one wallet/line → copy + smart signals),
`RPC_CONCURRENCY` (bound concurrent getTransaction calls to your credit budget),
`HOST`, `PORT`.

### Endpoints
| route | what |
|-------|------|
| `GET /health` | liveness + stats + active source |
| `GET /stats`  | swaps / tokens / graded+proven wallets / signal counts |
| `GET /signals?n=40` | live multi-detector feed |
| `GET /alpha?n=12&min_score=40` | top tokens by Alpha Score (+ component breakdown) |
| `WS  /stream` | pushes every parsed swap and periodic signal snapshots |

### Connect the dashboard
In `observation.html` → **Data** tab → **Server feed**, paste
`ws://<host>:8787/stream` and Connect. The dashboard ingests the server's swaps
directly (full coverage, no browser polling). Leave it blank to keep the
browser's own Helius polling.

## Transports
* **MockFirehose** — replays a fixed list; used by the offline test.
* **HeliusWsFirehose** — `logsSubscribe` on each DEX program id (Raydium,
  Pump.fun/PumpSwap, Meteora, Orca, LaunchLab, Moonshot…), then `getTransaction`
  (jsonParsed) → `UniversalSwapParser`. A semaphore bounds RPC concurrency;
  signatures are de-duped; auto-reconnects.
* **YellowstoneFirehose** — documented stub for the true Geyser/LaserStream gRPC
  firehose (lowest latency, paid plan). Generate the geyser protobuf stubs and
  map updates into the same swap dicts to drop it in without touching the engine.

## Tested offline
`tests/unit/test_firehose_ingestor.py` drives the engine end-to-end through
`MockFirehose` and validates the jsonParsed→swap parser on a fixture — no network
or web stack required (`pytest -k firehose`).

## Honesty
This removes the *coverage* ceiling and sharpens the grades/score with real
population data — it does not by itself guarantee profit. Validate edge in the
dashboard's backtester on the accumulated full-coverage dataset. The WebSocket
firehose still does one `getTransaction` per tx; for the lowest latency and
highest throughput, move to the Yellowstone gRPC seam.
