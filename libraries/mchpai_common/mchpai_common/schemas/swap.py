"""Rich swap schema — the atomic unit of the dataset.

This is the single normalized representation every DEX collapses into. It carries
everything downstream models need *and* everything required to reconstruct
ordered sequences later (slot + timestamp + signature give a total order).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from .common import Side


class Dex(str, Enum):
    """Every venue the universal parser recognizes."""

    pumpfun = "pumpfun"          # Pump.fun bonding curve
    pumpswap = "pumpswap"        # Pump.fun AMM (post-migration)
    raydium_amm = "raydium_amm"  # Raydium AMM v4
    raydium_clmm = "raydium_clmm"
    raydium_cpmm = "raydium_cpmm"
    launchlab = "launchlab"      # Raydium LaunchLab
    bonk = "bonk"                # LetsBonk / BonkFun (LaunchLab-based)
    meteora_dlmm = "meteora_dlmm"
    meteora_dyn = "meteora_dyn"  # Dynamic AMM pools
    meteora_dbc = "meteora_dbc"  # Dynamic Bonding Curve
    orca_whirlpool = "orca_whirlpool"
    jupiter = "jupiter"          # Jupiter aggregator (router)
    moonshot = "moonshot"
    unknown = "unknown"


class SwapEvent(BaseModel):
    """A single wallet's swap of SOL <-> a token on some DEX.

    ``sol_amount`` and ``token_amount`` are UI-denominated (post-decimals).
    ``price`` is SOL per token. ``market_cap`` is in SOL when supply is known.
    """

    signature: str
    slot: int
    timestamp: datetime
    dex: Dex

    wallet_address: str
    token_address: str           # the non-SOL mint
    side: Side

    sol_amount: float
    token_amount: float
    price: float | None = None           # SOL per token
    market_cap: float | None = None      # SOL (price * circulating supply)

    # provenance / sequence helpers
    instruction_index: int | None = None
    is_inner: bool = False
    program_id: str | None = None

    def signed_token_flow(self) -> float:
        """+token_amount on buy, -token_amount on sell (for cumulative supply held)."""
        return self.token_amount if self.side == Side.buy else -self.token_amount
