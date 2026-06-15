# Execution Engine (Rust)

The latency plane. A single multi-threaded `tokio` process
(`services/execution-engine`) with two concurrent halves.

## Ingest path

`Yellowstone gRPC (Geyser) → parse swaps → publish raw.swaps`

* `ingest/yellowstone.rs` — persistent gRPC subscription filtered to DEX programs
  (Pump.fun, Raydium AMM/CLMM, Meteora) to cut bandwidth at the source.
* `parser/swap.rs` — decodes instructions into a normalized `SwapEvent`
  (signer, mint, side, sol/token amounts, slot, ts, program).
* `signals/publisher.rs` — `XADD raw.swaps` (capped length) to Redis. No blocking
  I/O on the hot path.
* `ingest/helius.rs` — on-demand token metadata, cached in Redis with TTL.

## Execution path

`consume exec.orders → size guard → build tx → Jito tip → submit bundle → fills`

* `execution/mod.rs` — Redis consumer group on `exec.orders`; honors `exec:paused`
  every loop; at-least-once with XACK.
* `execution/sizing.rs` — defensive final size (risk shrink + hard ceiling).
* `execution/jito.rs` — builds the swap, prepends a tip to a rotating Jito tip
  account, submits the pair as a **bundle** to the block-engine for atomic,
  MEV-protected landing. Signing key from `WALLET_KEYPAIR_PATH`, never leaves the
  process.

## Latency budget (decision → land)

| Stage                                    | Target       |
|------------------------------------------|--------------|
| Yellowstone event → parsed              | < 15 ms      |
| publish + analytics predict + emit order | < 150 ms     |
| size + build + sign tx                   | < 10 ms      |
| Jito bundle submit → block-engine        | network RTT  |

## Optimizations

* Colocation near Yellowstone & Jito.
* Pre-warmed blockhash cache, pre-derived ATAs.
* Persistent HTTP/2 + gRPC connections; multiplexed Redis.
* Lock-free hot path; scores precomputed and cached in Redis so the live decision
  is a *lookup*, not a recompute.
* `panic = "abort"`, `lto`, `codegen-units = 1` in the release profile.

## Why Rust here (and only here)

The rest of the platform optimizes for iteration speed (Python). This path
optimizes for **predictable tail latency** — no GC pauses, tight control over the
submit→land pipeline, cheap parsing of large account/tx payloads.

## RPC rotation & resilience

`SOLANA_RPC_URLS` is a comma-separated pool; the engine rotates endpoints on
error/latency. Yellowstone reconnects with backoff; the execution loop survives
provider blips because orders sit durably in the Redis stream until ACKed.
