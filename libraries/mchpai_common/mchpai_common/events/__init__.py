"""Event-driven backbone.

Every service communicates *only* through events published to NATS JetStream.
This package defines:

* :class:`Envelope` — the uniform wrapper (id, type, version, ts, trace, payload)
* :mod:`subjects` — the canonical subject namespace (``mchpai.<domain>.<event>``)
* the typed **core event payloads** (TokenCreated, WalletBoughtToken, …)
* :class:`EventBus` — a thin async publish/subscribe client over JetStream

Adding a new event = add a payload model + a subject constant + a stream binding.
Nothing else in the platform needs to change to *carry* it.
"""

from .envelope import Envelope
from .types import (
    EventType,
    TokenCreated,
    TokenSnapshotEvent,
    WalletCreated,
    WalletUpdated,
    WalletBoughtToken,
    WalletSoldToken,
    LiquidityAdded,
    LiquidityRemoved,
    AttentionSpike,
    ClusterDetected,
    PredictionGenerated,
    BuySignalGenerated,
    TradeExecuted,
    PAYLOAD_BY_TYPE,
)
from . import subjects
from .bus import EventBus

__all__ = [
    "Envelope",
    "EventType",
    "EventBus",
    "subjects",
    "TokenCreated",
    "TokenSnapshotEvent",
    "WalletCreated",
    "WalletUpdated",
    "WalletBoughtToken",
    "WalletSoldToken",
    "LiquidityAdded",
    "LiquidityRemoved",
    "AttentionSpike",
    "ClusterDetected",
    "PredictionGenerated",
    "BuySignalGenerated",
    "TradeExecuted",
    "PAYLOAD_BY_TYPE",
]
