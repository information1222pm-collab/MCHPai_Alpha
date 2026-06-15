//! Execution path: consume sized orders → final sizing → Jito bundle submit.

pub mod jito;
pub mod sizing;

use anyhow::Result;
use redis::AsyncCommands;
use serde::Deserialize;
use tracing::{info, warn};

use crate::config::Config;
use crate::state::Metrics;

/// Order shape produced by the Python strategy-engine (subset we need here).
#[derive(Debug, Deserialize)]
pub struct Order {
    pub id: String,
    pub mint: String,
    pub size_sol: f64,
    #[serde(default)]
    pub max_slippage_bps: u32,
    #[serde(default)]
    pub jito_tip_lamports: Option<u64>,
    #[serde(default)]
    pub risk_score: Option<f64>,
}

const GROUP: &str = "execution-engine";
const CONSUMER: &str = "engine-1";

/// Run the execution half: read `exec.orders`, honor the kill-switch, size, and
/// submit. At-least-once via a Redis consumer group.
pub async fn run(cfg: Config, metrics: Metrics) -> Result<()> {
    let client = redis::Client::open(cfg.redis_url.clone())?;
    let mut conn = client.get_multiplexed_async_connection().await?;

    // Ensure the consumer group exists.
    let _: Result<(), _> = redis::cmd("XGROUP")
        .arg("CREATE")
        .arg(&cfg.orders_stream)
        .arg(GROUP)
        .arg("0")
        .arg("MKSTREAM")
        .query_async(&mut conn)
        .await;

    info!(stream = %cfg.orders_stream, mode = %cfg.execution_mode, "execution loop started");

    loop {
        // Global kill-switch.
        let paused: Option<String> = conn.get("exec:paused").await.ok().flatten();
        if paused.as_deref() == Some("1") {
            tokio::time::sleep(std::time::Duration::from_millis(250)).await;
            continue;
        }

        let reply: redis::streams::StreamReadReply = redis::cmd("XREADGROUP")
            .arg("GROUP").arg(GROUP).arg(CONSUMER)
            .arg("COUNT").arg(32)
            .arg("BLOCK").arg(2000)
            .arg("STREAMS").arg(&cfg.orders_stream).arg(">")
            .query_async(&mut conn)
            .await
            .unwrap_or_default();

        for stream in reply.keys {
            for entry in stream.ids {
                if let Some(redis::Value::Data(bytes)) = entry.map.get("data") {
                    if let Ok(order) = serde_json::from_slice::<Order>(bytes) {
                        metrics.orders_consumed.inc();
                        handle_order(&cfg, &metrics, &order).await;
                    } else {
                        warn!(id = %entry.id, "failed to parse order");
                    }
                }
                let _: Result<i64, _> = conn
                    .xack(&cfg.orders_stream, GROUP, &[entry.id.clone()])
                    .await;
            }
        }
    }
}

async fn handle_order(cfg: &Config, metrics: &Metrics, order: &Order) {
    let timer = metrics.exec_latency_ms.start_timer();

    // Final adaptive sizing guard (defense in depth on top of strategy-engine).
    let size = sizing::final_size(order.size_sol, order.risk_score.unwrap_or(50.0));
    if size <= 0.0 {
        timer.observe_duration();
        return;
    }

    if !cfg.is_live() {
        info!(mint = %order.mint, size_sol = size, "PAPER trade (dry-run)");
        timer.observe_duration();
        return;
    }

    match jito::submit_buy(cfg, &order.mint, size, order.jito_tip_lamports.unwrap_or(cfg.jito_tip_lamports)).await {
        Ok(bundle) => {
            metrics.trades_executed.inc();
            info!(mint = %order.mint, size_sol = size, bundle = %bundle, "trade submitted");
        }
        Err(e) => warn!(mint = %order.mint, error = %e, "trade submit failed"),
    }
    timer.observe_duration();
}
