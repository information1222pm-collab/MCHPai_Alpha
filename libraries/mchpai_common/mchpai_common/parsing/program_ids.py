"""Canonical Solana mainnet program IDs → :class:`Dex`.

These are real, well-known mainnet program addresses. Detection prefers the most
specific venue present; aggregator/router programs (Jupiter) are only used as a
fallback label when no concrete pool program is found, because a Jupiter swap is
*routed through* a concrete DEX whose program id is also present in the tx.
"""

from __future__ import annotations

from ..schemas.swap import Dex

WSOL_MINT = "So11111111111111111111111111111111111111112"
SYSTEM_PROGRAM = "11111111111111111111111111111111"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"

# program id -> Dex
DEX_BY_PROGRAM: dict[str, Dex] = {
    # Pump.fun
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P": Dex.pumpfun,
    "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA": Dex.pumpswap,
    # Raydium
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": Dex.raydium_amm,
    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK": Dex.raydium_clmm,
    "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C": Dex.raydium_cpmm,
    "LanMV9sAd7wArD4vJFi2qDdfnVhFxYSUg6eADduJ3uj": Dex.launchlab,  # LaunchLab / LetsBonk
    # Meteora
    "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo": Dex.meteora_dlmm,
    "Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB": Dex.meteora_dyn,
    "dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN": Dex.meteora_dbc,
    # Orca
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": Dex.orca_whirlpool,
    # Moonshot
    "MoonCVVNZFSYkqNXP6bxHLPL6QQJiMagDL3qcqUQTrG": Dex.moonshot,
    # Jupiter aggregator (router — fallback only)
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": Dex.jupiter,
}

# Concrete (non-router) venues take priority over the aggregator label.
_ROUTERS = {Dex.jupiter}


def detect_dex(program_ids: list[str]) -> Dex:
    """Pick the venue for a tx from the set of invoked program ids.

    Concrete pool programs win over routers; if only a router is present we label
    it as the router. Returns ``Dex.unknown`` when nothing matches.
    """
    concrete: list[Dex] = []
    routers: list[Dex] = []
    for pid in program_ids:
        dex = DEX_BY_PROGRAM.get(pid)
        if dex is None:
            continue
        (routers if dex in _ROUTERS else concrete).append(dex)
    if concrete:
        return concrete[0]
    if routers:
        return routers[0]
    return Dex.unknown


def is_swap_program(program_ids: list[str]) -> bool:
    return detect_dex(program_ids) is not Dex.unknown
