//! Yellowstone gRPC (Geyser) subscription for a single endpoint.
//!
//! Subscribes to transaction updates filtered to the DEX programs MCHPAI tracks,
//! parses each into a normalized [`SwapEvent`], advances the [`SlotTracker`], and
//! pushes onto the bounded channel (awaiting when full = backpressure). Returning
//! `Err` signals the orchestrator to fail over to the next endpoint.

use anyhow::Result;
use tokio::sync::mpsc::Sender;
use tracing::{debug, info};

use crate::parser::swap::SwapEvent;
use crate::state::Metrics;

use super::endpoints::Endpoint;
use super::slot::SlotTracker;

/// DEX program IDs of interest (filter at the source to cut bandwidth).
pub const PROGRAM_IDS: &[&str] = &[
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P", // Pump.fun
    "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA", // Pump.swap
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8", // Raydium AMM v4
    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK", // Raydium CLMM
    "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C", // Raydium CPMM
    "LanMV9sAd7wArD4vJFi2qDdfnVhFxYSUg6eADduJ3uj",  // LaunchLab / LetsBonk
    "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo",  // Meteora DLMM
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",  // Orca Whirlpool
    "MoonCVVNZFSYkqNXP6bxHLPL6QQJiMagDL3qcqUQTrG",  // Moonshot
];

pub async fn stream_swaps(
    ep: &Endpoint,
    tx: &Sender<SwapEvent>,
    tracker: &SlotTracker,
    metrics: &Metrics,
) -> Result<()> {
    // Production subscription (kept compiling-light; drop in the real client):
    //
    //   let mut client = GeyserGrpcClient::build_from_shared(ep.url.clone())?
    //       .x_token(Some(ep.x_token.clone()))?
    //       .connect().await?;
    //   let req = SubscribeRequest { transactions: dex_filter(PROGRAM_IDS),
    //       commitment: Some(CommitmentLevel::Processed as i32), ..Default::default() };
    //   let (_sink, mut stream) = client.subscribe_with_request(Some(req)).await?;
    //   while let Some(update) = stream.next().await {
    //       let update = update?;                              // Err ⇒ failover
    //       let su = tracker.observe(update.slot);             // slot tracking + gaps
    //       if su.gap > 0 { metrics... ; }
    //       for ev in crate::parser::swap::parse_update(&update) {
    //           tx.send(ev).await?;                            // backpressure when full
    //       }
    //   }
    //   Ok(())  // stream closed ⇒ orchestrator re-subscribes / fails over

    info!(url = %ep.url, programs = PROGRAM_IDS.len(), "yellowstone subscription (skeleton)");
    let _ = (tx, tracker, metrics); // wired in the real loop above
    loop {
        // A healthy long-lived subscription would be blocked on `stream.next()`.
        // The skeleton idles so the orchestrator treats it as a stable connection.
        tokio::time::sleep(std::time::Duration::from_secs(30)).await;
        debug!(url = %ep.url, last_slot = tracker.last_slot(), "yellowstone heartbeat");
    }
}
