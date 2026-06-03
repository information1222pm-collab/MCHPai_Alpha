//! Ingest path: Yellowstone gRPC (failover pool) → parse → bounded channel →
//! Redis publisher. This is the heart of the system.
//!
//! Architecture:
//!
//! ```text
//!   EndpointPool ──subscribe──> [Geyser stream] ──parse──> mpsc(bounded) ──> publisher ──> raw.swaps
//!        ▲ failover/backoff            │ slot tracking         │ backpressure
//!        └─────────── mark_failed ◀────┘                       └── XADD MAXLEN
//! ```
//!
//! * **Failover**: the producer rotates to the next healthy endpoint on any error.
//! * **Slot tracking**: every update advances the `SlotTracker`; gaps are counted.
//! * **Backpressure**: a bounded `mpsc` channel decouples the network stream from
//!   Redis. If Redis slows, the channel fills and the producer awaits — we slow
//!   ingestion rather than exhaust memory.

pub mod endpoints;
pub mod helius;
pub mod reconcile;
pub mod slot;
pub mod yellowstone;

use anyhow::Result;
use tokio::sync::mpsc;
use tracing::{info, warn};

use crate::config::Config;
use crate::parser::swap::SwapEvent;
use crate::signals::publisher;
use crate::state::Metrics;

use endpoints::EndpointPool;
use slot::SlotTracker;

pub async fn run(cfg: Config, metrics: Metrics) -> Result<()> {
    let pairs: Vec<(String, String)> = cfg
        .yellowstone_endpoints
        .iter()
        .cloned()
        .map(|u| (u, cfg.yellowstone_x_token.clone()))
        .collect();
    let pool = EndpointPool::new(pairs);

    if pool.is_empty() {
        warn!("no YELLOWSTONE endpoints configured — ingest idle (set YELLOWSTONE_ENDPOINTS)");
        futures::future::pending::<()>().await;
        return Ok(());
    }
    info!(endpoints = pool.len(), capacity = cfg.ingest_channel_capacity, "ingest starting");

    // Bounded channel = backpressure boundary between stream and publisher.
    let (tx, mut rx) = mpsc::channel::<SwapEvent>(cfg.ingest_channel_capacity);

    // Consumer: drain the channel into Redis as fast as it can.
    let publisher_cfg = cfg.clone();
    let pub_metrics = metrics.clone();
    let consumer = tokio::spawn(async move {
        let mut conn = match publisher::connect(&publisher_cfg).await {
            Ok(c) => c,
            Err(e) => {
                warn!(error = %e, "publisher connect failed");
                return;
            }
        };
        while let Some(ev) = rx.recv().await {
            if let Err(e) = publisher::publish_swap(&mut conn, &publisher_cfg.raw_swaps_stream, &ev).await {
                warn!(error = %e, "publish_swap failed");
            } else {
                pub_metrics.swaps_ingested.inc();
            }
        }
    });

    // Producer: failover loop over the endpoint pool with slot tracking.
    let tracker = SlotTracker::new();
    let producer = tokio::spawn(async move {
        loop {
            match pool.next_available() {
                Some(ep) => {
                    info!(url = %ep.url, "subscribing Yellowstone endpoint");
                    match yellowstone::stream_swaps(ep, &tx, &tracker, &metrics).await {
                        Ok(()) => ep.mark_ok(),
                        Err(e) => {
                            warn!(url = %ep.url, error = %e, "stream ended, failing over");
                            ep.mark_failed();
                        }
                    }
                }
                None => {
                    // all endpoints cooling down; wait before retrying
                    tokio::time::sleep(std::time::Duration::from_millis(500)).await;
                }
            }
        }
    });

    tokio::select! {
        _ = consumer => {}
        _ = producer => {}
    }
    Ok(())
}
