//! Environment-driven configuration (mirrors mchpai_common.config on the Python
//! side). Read once at startup; cheap to clone across tasks.

use std::env;

#[derive(Clone, Debug)]
pub struct Config {
    pub env: String,
    pub execution_mode: String, // paper | live

    pub redis_url: String,

    pub yellowstone_endpoint: String,
    pub yellowstone_x_token: String,
    pub helius_rpc_url: String,

    pub jito_block_engine_url: String,
    pub jito_tip_lamports: u64,
    pub wallet_keypair_path: String,

    pub raw_swaps_stream: String,
    pub orders_stream: String,
    pub fills_stream: String,

    pub metrics_port: u16,
}

fn get(key: &str, default: &str) -> String {
    env::var(key).unwrap_or_else(|_| default.to_string())
}

impl Config {
    pub fn from_env() -> Self {
        let _ = dotenvy::dotenv();
        Config {
            env: get("MCHPAI_ENV", "local"),
            execution_mode: get("EXECUTION_MODE", "paper"),
            redis_url: get("REDIS_URL", "redis://redis:6379/0"),
            yellowstone_endpoint: get("YELLOWSTONE_ENDPOINT", ""),
            yellowstone_x_token: get("YELLOWSTONE_X_TOKEN", ""),
            helius_rpc_url: get("HELIUS_RPC_URL", ""),
            jito_block_engine_url: get(
                "JITO_BLOCK_ENGINE_URL",
                "https://mainnet.block-engine.jito.wtf",
            ),
            jito_tip_lamports: get("JITO_TIP_LAMPORTS", "100000").parse().unwrap_or(100_000),
            wallet_keypair_path: get("WALLET_KEYPAIR_PATH", "/run/secrets/hot_wallet.json"),
            raw_swaps_stream: "raw.swaps".to_string(),
            orders_stream: "exec.orders".to_string(),
            fills_stream: "exec.fills".to_string(),
            metrics_port: get("EXEC_METRICS_PORT", "9100").parse().unwrap_or(9100),
        }
    }

    pub fn is_live(&self) -> bool {
        self.execution_mode == "live"
    }
}
