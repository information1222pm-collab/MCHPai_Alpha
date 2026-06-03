//! MCHPAI execution-engine.
//!
//! The latency-critical core of the platform. Two concurrent halves:
//!
//!   * **Ingest path**: Yellowstone gRPC (Geyser) → parse swaps → publish to the
//!     Redis `raw.swaps` stream for the Python analytics tier. Hot path, no
//!     blocking I/O, predictable tail latency.
//!   * **Execution path**: consume sized `exec.orders` (produced by the Python
//!     strategy-engine) → adaptive final sizing → build swap tx → attach Jito
//!     tip → submit bundle → write fills back to `exec.fills`.
//!
//! Everything is `tokio`, connections are persistent and pre-warmed, and the
//! global kill-switch (`exec:paused` in Redis) is honored every loop.
//!
//! Phase-0 note: several functions are integration seams (Helius enrichment,
//! Jito tip account, swap re-exports) that the real Yellowstone/Jito wiring will
//! call. They are intentionally present-but-unused in the skeleton, so dead-code
//! lints are relaxed crate-wide until that wiring lands.
#![allow(dead_code)]

mod config;
mod state;
mod ingest;
mod parser;
mod signals;
mod execution;

use anyhow::Result;
use tracing::info;

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .json()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info".into()),
        )
        .init();

    let cfg = config::Config::from_env();
    info!(env = %cfg.env, mode = %cfg.execution_mode, "execution-engine starting");

    // Start the Prometheus metrics endpoint.
    let metrics = state::Metrics::new();
    tokio::spawn(state::serve_metrics(cfg.metrics_port, metrics.clone()));

    // Two long-running halves; if either exits, the process exits.
    let ingest_task = {
        let cfg = cfg.clone();
        let metrics = metrics.clone();
        tokio::spawn(async move { ingest::run(cfg, metrics).await })
    };

    let exec_task = {
        let cfg = cfg.clone();
        let metrics = metrics.clone();
        tokio::spawn(async move { execution::run(cfg, metrics).await })
    };

    tokio::select! {
        r = ingest_task => { r??; }
        r = exec_task   => { r??; }
    }
    Ok(())
}
