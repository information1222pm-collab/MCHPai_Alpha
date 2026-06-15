//! Redis stream publisher for parsed swaps.
//!
//! The `raw.swaps` stream is the seam between the Rust hot path and the Python
//! analytics tier (`wallet-ingestion` consumes it). We serialize `SwapEvent` to
//! JSON under a single `data` field for a stable, language-neutral contract.

use anyhow::Result;
use redis::aio::MultiplexedConnection;
use redis::AsyncCommands;

use crate::config::Config;
use crate::parser::swap::SwapEvent;

/// Open a multiplexed Redis connection (cheap to clone, shared across the task).
pub async fn connect(cfg: &Config) -> Result<MultiplexedConnection> {
    let client = redis::Client::open(cfg.redis_url.clone())?;
    let conn = client.get_multiplexed_async_connection().await?;
    Ok(conn)
}

/// Publish one swap to the `raw.swaps` stream (capped length to bound memory).
pub async fn publish_swap(
    conn: &mut MultiplexedConnection,
    stream: &str,
    ev: &SwapEvent,
) -> Result<()> {
    let payload = serde_json::to_string(ev)?;
    // XADD raw.swaps MAXLEN ~ 1_000_000 * data <json>
    let _: String = conn
        .xadd_maxlen(stream, redis::streams::StreamMaxlen::Approx(1_000_000), "*", &[("data", payload)])
        .await?;
    Ok(())
}
