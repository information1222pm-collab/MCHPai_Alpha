"""Taxonomy of observed phenomena — reality, classified.

Astronomers do not redesign the telescope after one night. They observe, then
*classify*. This module is the classification instrument: pure functions that
sort raw provider payloads into named phenomenon classes. It changes nothing
about translation — it only *describes* what reality contains, so prevalence can
be measured before anything is "fixed".

A class here is not a bug and not a fix. It is a recurring shape reality
presents. When a shape proves common enough to matter, it earns a name here and
an entry in ``taxonomy.md``; the measured prevalence lives in ``distributions.md``.
"""

from __future__ import annotations

from enum import StrEnum

# Canonical rent-exempt minimum for a 165-byte SPL token account (lamports).
# Seen constantly in swaps as a temporary ATA deposit and its refund.
ATA_RENT_LAMPORTS = 2_039_280


class SwapShape(StrEnum):
    """How a swap's value legs are arranged — the axis BUG-001 lives on."""

    SOL_PAIRED_BUY = "sol_paired_buy"     # nativeInput + tokenOutputs  (translated)
    SOL_PAIRED_SELL = "sol_paired_sell"   # tokenInputs + nativeOutput  (translated)
    TOKEN_TO_TOKEN = "token_to_token"     # tokenInputs + tokenOutputs, no native legs
    NATIVE_ONLY = "native_only"           # native legs only, no token legs
    EMPTY = "empty"                       # a swap event with no recognizable legs
    NOT_A_SWAP = "not_a_swap"             # no events.swap at all


class NativeTransferClass(StrEnum):
    """What a SOL movement inside a transaction actually is — the axis BUG-002
    lives on. Most are swap mechanics, not genuine funding."""

    ATA_RENT = "ata_rent"        # exactly the token-account rent (deposit or refund)
    SELF = "self"                # from == to (no real counterparty)
    DUST = "dust"                # < 0.0001 SOL — fees/tips
    SMALL = "small"              # < 0.01 SOL
    MEDIUM = "medium"            # < 1 SOL
    LARGE = "large"              # >= 1 SOL


def _swap(tx: dict) -> dict | None:
    return (tx.get("events") or {}).get("swap")


def classify_swap_shape(tx: dict) -> SwapShape:
    """Sort a transaction by its swap-leg arrangement. Pure; reads only the
    payload."""
    sw = _swap(tx)
    if sw is None:
        return SwapShape.NOT_A_SWAP
    native_in = sw.get("nativeInput")
    native_out = sw.get("nativeOutput")
    token_in = sw.get("tokenInputs") or []
    token_out = sw.get("tokenOutputs") or []
    has_native = bool(native_in) or bool(native_out)
    has_token = bool(token_in) or bool(token_out)

    if native_in and token_out and not token_in:
        return SwapShape.SOL_PAIRED_BUY
    if token_in and native_out and not token_out:
        return SwapShape.SOL_PAIRED_SELL
    if has_token and not has_native:
        return SwapShape.TOKEN_TO_TOKEN
    if has_native and not has_token:
        return SwapShape.NATIVE_ONLY
    if not has_native and not has_token:
        return SwapShape.EMPTY
    # Mixed (native on one side, tokens on both, etc.) — count as token-to-token
    # since the SOL leg is incidental, not the pricing leg.
    return SwapShape.TOKEN_TO_TOKEN


def route_hops(tx: dict) -> int:
    """Number of inner swaps in a routed trade (Jupiter etc.). 0 if not a swap."""
    sw = _swap(tx)
    if sw is None:
        return 0
    return len(sw.get("innerSwaps") or [])


def is_multi_hop(tx: dict) -> bool:
    return route_hops(tx) > 1


def classify_native_transfer(amount: int, from_acct: str | None, to_acct: str | None) -> NativeTransferClass:
    """Classify one SOL movement by size and shape. Pure."""
    if from_acct is not None and from_acct == to_acct:
        return NativeTransferClass.SELF
    if int(amount) == ATA_RENT_LAMPORTS:
        return NativeTransferClass.ATA_RENT
    a = int(amount)
    if a < 100_000:           # < 0.0001 SOL
        return NativeTransferClass.DUST
    if a < 10_000_000:        # < 0.01 SOL
        return NativeTransferClass.SMALL
    if a < 1_000_000_000:     # < 1 SOL
        return NativeTransferClass.MEDIUM
    return NativeTransferClass.LARGE


def classify_native_transfers(tx: dict) -> list[NativeTransferClass]:
    """Classify every SOL movement in a transaction."""
    out: list[NativeTransferClass] = []
    for t in tx.get("nativeTransfers") or []:
        amount = t.get("amount", 0)
        out.append(classify_native_transfer(int(amount), t.get("fromUserAccount"), t.get("toUserAccount")))
    return out


def swap_source(tx: dict) -> str:
    """Reported routing source (JUPITER, RAYDIUM, PUMP_FUN, …) or the tx type."""
    return tx.get("source") or tx.get("type") or "UNKNOWN"
