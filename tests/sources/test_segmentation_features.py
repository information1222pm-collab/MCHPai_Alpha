"""The per-wallet feature extractor is pure and deterministic — it places a
wallet in behavioral space without imposing any category."""

from __future__ import annotations

from wis.research.segmentation_lab.features import (
    build_feature_table,
    extract_wallet_features,
    group_by_fee_payer,
)

T = 1_700_000_000
DAY = 86_400


def _swap_buy(wallet, t):
    return {"feePayer": wallet, "timestamp": t, "type": "SWAP", "events": {"swap": {
        "nativeInput": {"amount": "1000000000"},
        "tokenOutputs": [{"mint": "GEM", "rawTokenAmount": {"tokenAmount": "1", "decimals": 6}}]}}}


def _swap_t2t(wallet, t):
    return {"feePayer": wallet, "timestamp": t, "type": "SWAP", "source": "JUPITER", "events": {"swap": {
        "nativeInput": None, "nativeOutput": None,
        "tokenInputs": [{"mint": "USDC", "rawTokenAmount": {"tokenAmount": "1", "decimals": 6}}],
        "tokenOutputs": [{"mint": "GEM", "rawTokenAmount": {"tokenAmount": "1", "decimals": 6}}]}}}


def test_sol_paired_wallet_features() -> None:
    txs = [_swap_buy("w", T + i * DAY) for i in range(4)]
    f = extract_wallet_features("w", txs)
    assert f.n_parsed_swaps == 4
    assert f.frac_sol_paired == 1.0
    assert f.frac_token_to_token == 0.0
    assert f.log_avg_sol_trade > 0  # 1 SOL legs recorded


def test_token_to_token_router_features() -> None:
    txs = [_swap_t2t("w", T + i * DAY) for i in range(5)]
    f = extract_wallet_features("w", txs)
    assert f.frac_token_to_token == 1.0
    assert f.frac_sol_paired == 0.0
    assert f.jupiter_share == 1.0
    assert f.log_avg_sol_trade == 0.0  # no native legs


def test_grouping_and_table_filters_low_activity() -> None:
    txs = [_swap_buy("active", T + i * DAY) for i in range(20)] + [_swap_t2t("sparse", T)]
    grouped = group_by_fee_payer(txs)
    assert set(grouped) == {"active", "sparse"}
    table = build_feature_table(grouped, min_txs=15)
    # Only the active wallet survives the min-tx filter (small denominators lie).
    assert table.wallets == ["active"]
    assert len(table.rows) == 1 and len(table.rows[0]) == len(table.feature_keys)


def test_features_are_deterministic() -> None:
    txs = [_swap_buy("w", T), _swap_t2t("w", T + DAY)]
    assert extract_wallet_features("w", txs) == extract_wallet_features("w", txs)
