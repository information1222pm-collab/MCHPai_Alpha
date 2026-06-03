//! Swap decoding → normalized `SwapEvent`.
//!
//! Each supported program (Pump.fun, Raydium, Meteora) has its own instruction
//! layout; we decode the relevant ones into a single normalized struct so the
//! rest of the platform is venue-agnostic. The struct shape matches the JSON the
//! Python `wallet-ingestion` service expects on `raw.swaps`.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum SwapSide {
    Buy,
    Sell,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SwapEvent {
    pub signature: String,
    pub wallet: String,
    pub mint: String,
    pub side: SwapSide,
    pub sol_amount: f64,
    pub token_amount: f64,
    pub price_sol: Option<f64>,
    pub program: String,
    pub slot: u64,
    /// Unix seconds; matches the Python side's `ts` field.
    pub ts: i64,
}

impl SwapEvent {
    pub fn price(&self) -> Option<f64> {
        if self.token_amount > 0.0 {
            Some(self.sol_amount / self.token_amount)
        } else {
            None
        }
    }
}

/// Placeholder hook so the ingest skeleton links cleanly. The production parser
/// takes a Yellowstone `SubscribeUpdateTransaction` and returns `Option<SwapEvent>`.
pub fn noop() {}
