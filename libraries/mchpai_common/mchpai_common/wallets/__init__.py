"""Wallet domain logic: behavioral profiling from raw trade history.

This is the foundation of every wallet score. Given a wallet's chronological
trades, :func:`profile_wallet` produces the six behavioral axes via FIFO
round-trip matching so that *only realized* performance is measured.
"""

from .profiling import profile_wallet, RoundTrip, match_round_trips

__all__ = ["profile_wallet", "RoundTrip", "match_round_trips"]
