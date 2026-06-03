//! Jito bundle submission.
//!
//! Builds a swap transaction, prepends a tip instruction to a Jito tip account,
//! and submits the pair as a bundle to the Jito block-engine for atomic,
//! MEV-protected landing. The signing key is loaded from `WALLET_KEYPAIR_PATH`
//! and never leaves the process.
//!
//! Latency optimizations (production): pre-warmed blockhash cache, pre-derived
//! ATAs, persistent HTTP/2 connection to the block-engine, and colocation.

use anyhow::Result;

use crate::config::Config;

/// Submit a buy as a Jito bundle. Returns the bundle id on success.
///
/// Skeleton: in `paper` mode the caller never reaches here; in `live` mode this
/// is where the real build+sign+submit happens. We keep the signature stable so
/// the execution loop is complete and testable.
pub async fn submit_buy(
    cfg: &Config,
    mint: &str,
    size_sol: f64,
    tip_lamports: u64,
) -> Result<String> {
    // Production outline:
    //   1. let keypair = read_keypair_file(&cfg.wallet_keypair_path)?;
    //   2. let route = jupiter_quote(mint, size_sol, max_slippage).await?;
    //   3. let swap_ix = build_swap_ix(&route, &keypair.pubkey());
    //   4. let tip_ix  = system_instruction::transfer(&keypair.pubkey(),
    //                       &jito_tip_account(), tip_lamports);
    //   5. let tx = sign_tx(vec![tip_ix, swap_ix], recent_blockhash, &keypair);
    //   6. let bundle_id = post_bundle(&cfg.jito_block_engine_url, &[tx]).await?;
    //   7. confirm_via_yellowstone(bundle_id).await?;
    let _ = (cfg, size_sol);
    let bundle_id = format!("paper-bundle-{mint}-{tip_lamports}");
    Ok(bundle_id)
}

/// One of the rotating Jito tip accounts (production rotates across all eight).
pub fn jito_tip_account() -> &'static str {
    "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5"
}
