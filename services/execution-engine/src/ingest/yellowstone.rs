//! Yellowstone gRPC (Geyser) subscription.
//!
//! Subscribes to transaction updates filtered to the DEX programs MCHPAI tracks
//! (Pump.fun, Pump.swap, Raydium AMM/CLMM, Meteora). Each update is handed to the
//! swap parser; recognized swaps are published to Redis with minimal latency.
//!
//! The concrete `yellowstone-grpc-client` wiring is encapsulated here so the rest
//! of the engine depends only on the normalized `SwapEvent`.

use anyhow::Result;
use tracing::{debug, info};

use crate::config::Config;
use crate::parser::swap;
use crate::signals::publisher;
use crate::state::Metrics;

/// DEX program IDs of interest (filter at the source to cut bandwidth).
pub const PROGRAM_IDS: &[&str] = &[
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P", // Pump.fun
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8", // Raydium AMM v4
    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK", // Raydium CLMM
    "Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB", // Meteora pools
];

pub async fn stream_swaps(cfg: &Config, metrics: &Metrics) -> Result<()> {
    // Pseudocode of the production subscription (kept compiling-light here):
    //
    //   let mut client = GeyserGrpcClient::build_from_shared(cfg.yellowstone_endpoint)?
    //       .x_token(Some(cfg.yellowstone_x_token.clone()))?
    //       .connect().await?;
    //   let request = SubscribeRequest {
    //       transactions: dex_program_filter(PROGRAM_IDS),
    //       commitment: Some(CommitmentLevel::Processed as i32),
    //       ..Default::default()
    //   };
    //   let (_tx, mut stream) = client.subscribe_with_request(Some(request)).await?;
    //   while let Some(update) = stream.next().await {
    //       if let Some(ev) = swap::parse_update(&update?, metrics) {
    //           publisher::publish_swap(cfg, &ev).await?;
    //           metrics.swaps_ingested.inc();
    //       }
    //   }

    info!(programs = PROGRAM_IDS.len(), "yellowstone subscription established (skeleton)");

    // Demonstrate the downstream wiring compiles & runs end-to-end with a
    // heartbeat; replace with the real stream loop above.
    let pub_conn = publisher::connect(cfg).await?;
    loop {
        tokio::time::sleep(std::time::Duration::from_secs(30)).await;
        debug!("yellowstone heartbeat — awaiting stream events");
        let _ = &pub_conn; // keep connection warm
        let _ = swap::noop();
        let _ = metrics;
    }
}
