"""Exact money representation.

Floating point is forbidden for value-bearing quantities. IEEE rounding drift
would make replay non-deterministic and corrupt cost-basis accounting over
billions of transactions. We store every amount as an *integer in its smallest
unit* plus a decimals scale, and do all ledger arithmetic in exact rationals
(:class:`fractions.Fraction`). Floats appear only at the reporting boundary,
for inherently-statistical scores (Sharpe, etc.), never in the ledger.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True, slots=True)
class Amount:
    """A non-negative quantity of some asset, exact to the smallest unit.

    ``raw`` is the integer count of the smallest unit (e.g. lamports), and
    ``decimals`` is how many of those units make one whole token.
    """

    raw: int
    decimals: int

    def __post_init__(self) -> None:
        if self.raw < 0:
            raise ValueError(f"Amount cannot be negative: {self.raw}")
        if self.decimals < 0:
            raise ValueError(f"decimals cannot be negative: {self.decimals}")

    def as_fraction(self) -> Fraction:
        """Exact whole-token value as a rational number."""
        return Fraction(self.raw, 10**self.decimals)

    def is_zero(self) -> bool:
        return self.raw == 0

    def __str__(self) -> str:
        return f"{float(self.as_fraction()):.{min(self.decimals, 9)}f}"
