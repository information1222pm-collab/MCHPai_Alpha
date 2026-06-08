"""Strongly-typed identifiers.

Anonymous addresses are the raw material we refine into understandable
entities. We wrap them in distinct value types so the type checker enforces
that a token mint is never accidentally used where a wallet address is
expected — the kind of error that silently corrupts intelligence systems.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WalletAddress:
    """A market participant. The unit of intelligence in this system."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("WalletAddress cannot be empty")

    def short(self) -> str:
        return self.value if len(self.value) <= 10 else f"{self.value[:4]}…{self.value[-4:]}"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class TokenMint:
    """An asset a wallet can hold, buy, or sell."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("TokenMint cannot be empty")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ClusterId:
    """An emergent community of related wallets. Clusters are movies, not
    snapshots — a ClusterId is stable across time while its membership evolves."""

    value: str

    def __str__(self) -> str:
        return self.value
