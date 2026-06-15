"""Universal swap parsing.

Collapses transactions from every supported DEX (Pump.fun, Pump.swap, Raydium
AMM/CLMM/CPMM, LaunchLab, Bonk, Meteora DLMM/Dynamic/DBC, Orca Whirlpool,
Jupiter, Moonshot) into a single normalized :class:`SwapEvent`.

Strategy: rather than brittle per-DEX instruction decoding, we extract economic
truth from **balance deltas** in the transaction meta (pre/post SOL + token
balances per owner) and use **program-id detection** to label the venue. This is
how robust indexers work — it survives DEX upgrades and inner-instruction routing
(e.g. Jupiter → Raydium) that pure discriminator decoding misses.
"""

from .program_ids import DEX_BY_PROGRAM, detect_dex, WSOL_MINT
from .parser import TxContext, TokenBalance, UniversalSwapParser, parse_transaction

__all__ = [
    "DEX_BY_PROGRAM",
    "detect_dex",
    "WSOL_MINT",
    "TxContext",
    "TokenBalance",
    "UniversalSwapParser",
    "parse_transaction",
]
