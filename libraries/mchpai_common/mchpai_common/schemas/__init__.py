"""Domain schemas — the versioned data contracts of the platform.

These pydantic models are the *lingua franca* between services. They are
intentionally storage-agnostic (they map onto Postgres/ClickHouse/Neo4j but are
not coupled to any of them) and forward-compatible: add fields with defaults,
never repurpose meaning, bump ``SCHEMA_VERSION`` on breaking changes.
"""

from .common import SCHEMA_VERSION, Side, TokenSource, WalletLabel
from .token import Token, TokenSnapshot
from .wallet import Wallet, WalletProfile
from .trade import Trade
from .cluster import Cluster
from .scores import (
    WalletScore,
    ClusterScore,
    Prediction,
    RiskAssessment,
)
from .execution import Order, Fill, Position

__all__ = [
    "SCHEMA_VERSION",
    "Side",
    "TokenSource",
    "WalletLabel",
    "Token",
    "TokenSnapshot",
    "Wallet",
    "WalletProfile",
    "Trade",
    "Cluster",
    "WalletScore",
    "ClusterScore",
    "Prediction",
    "RiskAssessment",
    "Order",
    "Fill",
    "Position",
]
