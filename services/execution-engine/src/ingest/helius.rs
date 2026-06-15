//! Helius enrichment: on-demand token metadata / mint authority / LP info.
//!
//! Results are cached in Redis with a TTL so the hot path is a lookup, not an
//! RPC round-trip. Only called for tokens we don't already have cached.

use anyhow::Result;
use serde::Deserialize;

use crate::config::Config;

#[derive(Debug, Deserialize, Default)]
pub struct TokenMeta {
    pub mint: String,
    pub decimals: Option<u8>,
    pub mint_authority: Option<String>,
    pub freeze_authority: Option<String>,
}

/// Fetch (and cache) token metadata via Helius. Skeleton returns defaults when
/// no API key is configured so the engine runs without external creds.
pub async fn enrich_token(cfg: &Config, mint: &str) -> Result<TokenMeta> {
    if cfg.helius_rpc_url.is_empty() {
        return Ok(TokenMeta { mint: mint.to_string(), ..Default::default() });
    }
    // Production: POST getAsset / getTokenAccounts to cfg.helius_rpc_url and map
    // the response into TokenMeta, caching under `token:meta:{mint}` in Redis.
    Ok(TokenMeta { mint: mint.to_string(), ..Default::default() })
}
