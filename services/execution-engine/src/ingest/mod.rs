//! Ingest path: Yellowstone gRPC subscription → parse → publish to Redis.

pub mod yellowstone;
pub mod helius;

use anyhow::Result;
use tracing::{info, warn};

use crate::config::Config;
use crate::state::Metrics;

/// Run the ingest half: connect to Yellowstone, stream transactions for the DEX
/// programs we care about, parse swaps, and publish to the `raw.swaps` stream.
pub async fn run(cfg: Config, metrics: Metrics) -> Result<()> {
    if cfg.yellowstone_endpoint.is_empty() {
        warn!("YELLOWSTONE_ENDPOINT not set — ingest path idle (configure to enable)");
        // Idle forever so the process stays up (execution path may still run).
        futures::future::pending::<()>().await;
        return Ok(());
    }

    info!(endpoint = %cfg.yellowstone_endpoint, "connecting Yellowstone gRPC");
    yellowstone::stream_swaps(&cfg, &metrics).await
}
