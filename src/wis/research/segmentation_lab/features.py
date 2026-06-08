"""Per-wallet behavioral features — the coordinates of the segmentation space.

Phase 6 showed that ``P(BUG-001 | active_traders)`` ranges 28%–75% across fresh
samples on solid denominators. That variance is not noise; it is the signature of
*latent classes*. "Active trader" was a human label, not a population. To find the
populations reality actually has, we first need to place each wallet in a
behavioral space — and then let unsupervised methods (not our assumptions) draw
the boundaries.

This module is the pure, dependency-free feature extractor: from a wallet's raw
transactions it computes behavioral *ratios* (shape mix, venue mix, mechanics
share, sizing, tempo) — deliberately scale-free where possible, so clusters
reflect *behavior*, not merely activity volume. It changes nothing about
translation; it only describes.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from wis.research.reality_lab import taxonomy as tax

_MECHANICS = {tax.NativeTransferClass.DUST, tax.NativeTransferClass.ATA_RENT, tax.NativeTransferClass.SELF}
_SOL_SHAPES = {tax.SwapShape.SOL_PAIRED_BUY, tax.SwapShape.SOL_PAIRED_SELL}


@dataclass(frozen=True, slots=True)
class WalletFeatures:
    wallet: str
    n_txs: int
    n_parsed_swaps: int
    # behavioral ratios (the clustering coordinates)
    frac_token_to_token: float   # of parsed swaps — the BUG-001 axis
    frac_sol_paired: float       # of parsed swaps
    jupiter_share: float         # of parsed swaps
    frac_swap: float             # of txs
    frac_transfer: float         # of txs
    frac_unknown: float          # of txs
    native_transfer_ratio: float # native transfers per tx
    mechanics_ratio: float       # of native transfers (dust+rent+self)
    log_avg_sol_trade: float     # log1p mean SOL size of sol-paired legs
    log_counterparties: float    # log1p distinct native-transfer counterparties
    log_tx_per_day: float        # log1p activity tempo

    def to_vector(self, keys: Sequence[str]) -> list[float]:
        return [float(getattr(self, k)) for k in keys]


# The default clustering coordinates: behavioral, mostly scale-free.
FEATURE_KEYS: tuple[str, ...] = (
    "frac_token_to_token",
    "frac_sol_paired",
    "jupiter_share",
    "frac_swap",
    "frac_transfer",
    "frac_unknown",
    "native_transfer_ratio",
    "mechanics_ratio",
    "log_avg_sol_trade",
    "log_counterparties",
    "log_tx_per_day",
)


def _native_leg_lamports(swap: dict) -> int | None:
    for leg in ("nativeInput", "nativeOutput"):
        obj = swap.get(leg)
        if obj and obj.get("amount") is not None:
            return int(obj["amount"])
    return None


def extract_wallet_features(wallet: str, txs: Sequence[dict]) -> WalletFeatures:
    """Pure: a wallet's transactions → its behavioral feature vector."""
    n = len(txs)
    types: Counter[str] = Counter()
    shapes: Counter[tax.SwapShape] = Counter()
    n_swaps = 0
    jup = 0
    n_native = 0
    mech = 0
    counterparties: set[str] = set()
    sol_sizes: list[int] = []
    times: list[int] = []

    for tx in txs:
        types[tx.get("type")] += 1
        ts = tx.get("timestamp")
        if ts:
            times.append(int(ts))

        if (tx.get("events") or {}).get("swap"):
            n_swaps += 1
            shape = tax.classify_swap_shape(tx)
            shapes[shape] += 1
            if tax.swap_source(tx) == "JUPITER":
                jup += 1
            if shape in _SOL_SHAPES:
                lam = _native_leg_lamports(tx["events"]["swap"])
                if lam:
                    sol_sizes.append(lam)

        for t in tx.get("nativeTransfers") or []:
            n_native += 1
            cls = tax.classify_native_transfer(int(t.get("amount", 0)), t.get("fromUserAccount"), t.get("toUserAccount"))
            if cls in _MECHANICS:
                mech += 1
            for side in ("fromUserAccount", "toUserAccount"):
                a = t.get(side)
                if a and a != wallet:
                    counterparties.add(a)

    def ratio(a: int, b: int) -> float:
        return a / b if b else 0.0

    span_days = ((max(times) - min(times)) / 86_400) if len(times) >= 2 else 0.0
    tx_per_day = n / span_days if span_days > 0 else float(n)
    avg_sol = (sum(sol_sizes) / len(sol_sizes) / 1e9) if sol_sizes else 0.0

    return WalletFeatures(
        wallet=wallet,
        n_txs=n,
        n_parsed_swaps=n_swaps,
        frac_token_to_token=ratio(shapes.get(tax.SwapShape.TOKEN_TO_TOKEN, 0), n_swaps),
        frac_sol_paired=ratio(sum(shapes.get(s, 0) for s in _SOL_SHAPES), n_swaps),
        jupiter_share=ratio(jup, n_swaps),
        frac_swap=ratio(types.get("SWAP", 0), n),
        frac_transfer=ratio(types.get("TRANSFER", 0), n),
        frac_unknown=ratio(types.get("UNKNOWN", 0), n),
        native_transfer_ratio=ratio(n_native, n),
        mechanics_ratio=ratio(mech, n_native),
        log_avg_sol_trade=math.log1p(avg_sol),
        log_counterparties=math.log1p(len(counterparties)),
        log_tx_per_day=math.log1p(tx_per_day),
    )


def group_by_fee_payer(txs: Iterable[dict]) -> dict[str, list[dict]]:
    """Group raw transactions by their fee payer (the initiating wallet)."""
    out: dict[str, list[dict]] = {}
    for tx in txs:
        fp = tx.get("feePayer")
        if fp:
            out.setdefault(fp, []).append(tx)
    return out


@dataclass(frozen=True, slots=True)
class FeatureTable:
    wallets: list[str]
    feature_keys: tuple[str, ...]
    rows: list[list[float]]
    n_txs: list[int]
    n_swaps: list[int]


def build_feature_table(
    grouped: dict[str, list[dict]],
    *,
    min_txs: int = 15,
    feature_keys: tuple[str, ...] = FEATURE_KEYS,
) -> FeatureTable:
    """Build the wallet×feature matrix, keeping only wallets with enough activity
    that their ratios are meaningful (small denominators lie — Statistics Rule 2)."""
    wallets, rows, n_txs, n_swaps = [], [], [], []
    for wallet, wtxs in sorted(grouped.items()):
        if len(wtxs) < min_txs:
            continue
        f = extract_wallet_features(wallet, wtxs)
        wallets.append(wallet)
        rows.append(f.to_vector(feature_keys))
        n_txs.append(f.n_txs)
        n_swaps.append(f.n_parsed_swaps)
    return FeatureTable(wallets=wallets, feature_keys=feature_keys, rows=rows, n_txs=n_txs, n_swaps=n_swaps)
