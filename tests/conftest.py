"""Shared test helpers.

A small scenario builder so tests can express wallet behavior as a readable
script of buys/sells, and a deterministic clock so ingestion times are exact.
"""

from __future__ import annotations

from dataclasses import dataclass

from wis.domain.events import (
    DomainEvent,
    TokenPriceObserved,
    WalletBoughtToken,
    WalletCreated,
    WalletFunded,
    WalletSoldToken,
)
from wis.domain.identifiers import TokenMint, WalletAddress
from wis.domain.money import Amount
from wis.domain.time import DAY, Nanos
from wis.eventsourcing.store import InMemoryEventStore

LAMPORTS = 9  # decimals for the quote asset (SOL-like)
TOKEN_DECIMALS = 6


def sol(amount: float) -> Amount:
    return Amount(raw=int(round(amount * 10**LAMPORTS)), decimals=LAMPORTS)


def tokens(amount: float) -> Amount:
    return Amount(raw=int(round(amount * 10**TOKEN_DECIMALS)), decimals=TOKEN_DECIMALS)


@dataclass(slots=True)
class Scenario:
    """Appends events with monotonically increasing event- and ingestion-time."""

    store: InMemoryEventStore
    t: int = DAY  # current event time in nanos; starts at day 1 to avoid 0

    def _append(self, payload: DomainEvent, *, advance: int = 60_000_000_000) -> None:
        # ingestion lags event time by a fixed, deterministic amount.
        self.store.append(payload, ingestion_time=Nanos(self.t + 1_000_000_000))
        self.t += advance

    def created(self, wallet: str, funded_by: str | None = None) -> None:
        self._append(
            WalletCreated(
                occurred_at=Nanos(self.t),
                wallet=WalletAddress(wallet),
                funded_by=WalletAddress(funded_by) if funded_by else None,
            )
        )

    def funded(self, source: str, target: str, amount: float) -> None:
        self._append(
            WalletFunded(
                occurred_at=Nanos(self.t),
                source=WalletAddress(source),
                target=WalletAddress(target),
                amount=sol(amount),
            )
        )

    def price(self, token: str, price: float) -> None:
        self._append(
            TokenPriceObserved(
                occurred_at=Nanos(self.t),
                token=TokenMint(token),
                price_quote_per_base=sol(price),
            )
        )

    def buy(self, wallet: str, token: str, base: float, quote: float, *, advance: int = DAY) -> None:
        self._append(
            WalletBoughtToken(
                occurred_at=Nanos(self.t),
                wallet=WalletAddress(wallet),
                token=TokenMint(token),
                base=tokens(base),
                quote=sol(quote),
            ),
            advance=advance,
        )

    def sell(self, wallet: str, token: str, base: float, quote: float, *, advance: int = DAY) -> None:
        self._append(
            WalletSoldToken(
                occurred_at=Nanos(self.t),
                wallet=WalletAddress(wallet),
                token=TokenMint(token),
                base=tokens(base),
                quote=sol(quote),
            ),
            advance=advance,
        )
