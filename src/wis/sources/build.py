"""Event construction helpers shared by every source's translator.

Centralising how raw observations become domain events guarantees that a buy
from Helius and a buy from an archive are byte-for-byte the same event. Amounts
are accepted either as on-chain raw integers (base units + decimals — the chain
representation) or as human floats, and converted into the exact
:class:`Amount` value object the same way every time.
"""

from __future__ import annotations

from wis.domain.events import (
    TokenPriceObserved,
    WalletBoughtToken,
    WalletCreated,
    WalletFunded,
    WalletSoldToken,
)
from wis.domain.identifiers import TokenMint, WalletAddress
from wis.domain.money import Amount
from wis.domain.time import Nanos


def amount_from_raw(raw: int, decimals: int) -> Amount:
    """From on-chain base units (the preferred, lossless path)."""
    return Amount(raw=int(raw), decimals=int(decimals))


def amount_from_float(value: float, decimals: int) -> Amount:
    """From a human quantity. Rounds to the smallest unit deterministically."""
    return Amount(raw=int(round(value * 10**decimals)), decimals=int(decimals))


def created(wallet: str, at: int, funded_by: str | None = None) -> WalletCreated:
    return WalletCreated(
        occurred_at=Nanos(at),
        wallet=WalletAddress(wallet),
        funded_by=WalletAddress(funded_by) if funded_by else None,
    )


def funding(source: str, target: str, amount: Amount, at: int) -> WalletFunded:
    return WalletFunded(
        occurred_at=Nanos(at),
        source=WalletAddress(source),
        target=WalletAddress(target),
        amount=amount,
    )


def price(token: str, price_quote_per_base: Amount, at: int) -> TokenPriceObserved:
    return TokenPriceObserved(
        occurred_at=Nanos(at),
        token=TokenMint(token),
        price_quote_per_base=price_quote_per_base,
    )


def buy(wallet: str, token: str, base: Amount, quote: Amount, at: int, venue: str | None = None) -> WalletBoughtToken:
    return WalletBoughtToken(
        occurred_at=Nanos(at),
        wallet=WalletAddress(wallet),
        token=TokenMint(token),
        base=base,
        quote=quote,
        venue=venue,
    )


def sell(wallet: str, token: str, base: Amount, quote: Amount, at: int, venue: str | None = None) -> WalletSoldToken:
    return WalletSoldToken(
        occurred_at=Nanos(at),
        wallet=WalletAddress(wallet),
        token=TokenMint(token),
        base=base,
        quote=quote,
        venue=venue,
    )
