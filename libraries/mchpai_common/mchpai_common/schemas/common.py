"""Shared enums and the global schema version."""

from __future__ import annotations

from enum import Enum

# Bump on breaking changes to any schema; events carry this for compatibility.
SCHEMA_VERSION = "1"


class Side(str, Enum):
    buy = "buy"
    sell = "sell"


class TokenSource(str, Enum):
    pumpfun = "pumpfun"
    pumpswap = "pumpswap"
    raydium = "raydium"
    meteora = "meteora"
    jupiter = "jupiter"
    birdeye = "birdeye"
    helius = "helius"
    yellowstone = "yellowstone"
    unknown = "unknown"


class WalletLabel(str, Enum):
    sniper = "sniper"
    insider = "insider"
    market_maker = "market_maker"
    smart_money = "smart_money"
    bot = "bot"
    retail = "retail"
    bundler = "bundler"
    unknown = "unknown"
