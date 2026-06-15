"""Core event payload definitions and their wiring to subjects.

These thirteen events are the platform's vocabulary. Each maps to one subject and
one typed payload. ``PAYLOAD_BY_TYPE`` lets consumers deserialize an
:class:`~mchpai_common.events.envelope.Envelope` back into the right model.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from ..schemas.common import Side, TokenSource
from . import subjects


class EventType(str, Enum):
    TOKEN_CREATED = "TokenCreated"
    TOKEN_SNAPSHOT = "TokenSnapshot"
    WALLET_CREATED = "WalletCreated"
    WALLET_UPDATED = "WalletUpdated"
    WALLET_BOUGHT_TOKEN = "WalletBoughtToken"
    WALLET_SOLD_TOKEN = "WalletSoldToken"
    LIQUIDITY_ADDED = "LiquidityAdded"
    LIQUIDITY_REMOVED = "LiquidityRemoved"
    ATTENTION_SPIKE = "AttentionSpike"
    CLUSTER_DETECTED = "ClusterDetected"
    PREDICTION_GENERATED = "PredictionGenerated"
    BUY_SIGNAL_GENERATED = "BuySignalGenerated"
    TRADE_EXECUTED = "TradeExecuted"


# ---- token events ----------------------------------------------------------
class TokenCreated(BaseModel):
    mint: str
    symbol: str | None = None
    name: str | None = None
    creator: str | None = None
    source: TokenSource = TokenSource.unknown
    created_at: datetime | None = None
    initial_liquidity_sol: float | None = None


class TokenSnapshotEvent(BaseModel):
    mint: str
    ts: datetime
    price_sol: float | None = None
    liquidity_sol: float | None = None
    holders: int | None = None
    volume_1m: float | None = None
    buys_1m: int | None = None
    sells_1m: int | None = None


# ---- wallet events ---------------------------------------------------------
class WalletCreated(BaseModel):
    address: str
    first_seen_at: datetime | None = None
    funded_by: str | None = None


class WalletUpdated(BaseModel):
    address: str
    label: str | None = None
    alpha_score: float | None = None


class WalletBoughtToken(BaseModel):
    wallet: str
    mint: str
    signature: str
    sol_amount: float
    token_amount: float
    price_sol: float | None = None
    slot: int | None = None
    block_time: datetime | None = None
    program: str | None = None


class WalletSoldToken(BaseModel):
    wallet: str
    mint: str
    signature: str
    sol_amount: float
    token_amount: float
    price_sol: float | None = None
    slot: int | None = None
    block_time: datetime | None = None
    program: str | None = None


# ---- liquidity events ------------------------------------------------------
class LiquidityAdded(BaseModel):
    mint: str
    pool: str | None = None
    sol_amount: float
    ts: datetime | None = None
    provider: str | None = None


class LiquidityRemoved(BaseModel):
    mint: str
    pool: str | None = None
    sol_amount: float
    ts: datetime | None = None
    provider: str | None = None


# ---- signal events ---------------------------------------------------------
class AttentionSpike(BaseModel):
    mint: str
    attention: float
    velocity: float
    entropy: float | None = None
    r0: float | None = None
    ts: datetime | None = None


class ClusterDetected(BaseModel):
    cluster_id: str
    members: list[str] = Field(default_factory=list)
    cluster_score: float
    method: str = "louvain"
    shared_funder: str | None = None


class PredictionGenerated(BaseModel):
    mint: str
    model_version: str
    buy_probability: float
    expected_value: float
    risk_score: float
    top_cluster_id: str | None = None
    alpha_buyers: list[str] = Field(default_factory=list)


class BuySignalGenerated(BaseModel):
    signal_id: str
    mint: str
    size_sol: float
    expected_value: float
    risk_score: float
    buy_probability: float


# ---- execution events ------------------------------------------------------
class TradeExecuted(BaseModel):
    position_id: str
    mint: str
    side: Side
    sol_amount: float
    token_amount: float
    signature: str | None = None
    jito_bundle: str | None = None
    latency_ms: int | None = None
    landed_slot: int | None = None


# ---- registry --------------------------------------------------------------
SUBJECT_BY_TYPE: dict[EventType, str] = {
    EventType.TOKEN_CREATED: subjects.TOKEN_CREATED,
    EventType.TOKEN_SNAPSHOT: subjects.TOKEN_SNAPSHOT,
    EventType.WALLET_CREATED: subjects.WALLET_CREATED,
    EventType.WALLET_UPDATED: subjects.WALLET_UPDATED,
    EventType.WALLET_BOUGHT_TOKEN: subjects.WALLET_BOUGHT,
    EventType.WALLET_SOLD_TOKEN: subjects.WALLET_SOLD,
    EventType.LIQUIDITY_ADDED: subjects.LIQUIDITY_ADDED,
    EventType.LIQUIDITY_REMOVED: subjects.LIQUIDITY_REMOVED,
    EventType.ATTENTION_SPIKE: subjects.ATTENTION_SPIKE,
    EventType.CLUSTER_DETECTED: subjects.CLUSTER_DETECTED,
    EventType.PREDICTION_GENERATED: subjects.PREDICTION_GENERATED,
    EventType.BUY_SIGNAL_GENERATED: subjects.BUY_SIGNAL,
    EventType.TRADE_EXECUTED: subjects.TRADE_EXECUTED,
}

PAYLOAD_BY_TYPE: dict[str, type[BaseModel]] = {
    EventType.TOKEN_CREATED.value: TokenCreated,
    EventType.TOKEN_SNAPSHOT.value: TokenSnapshotEvent,
    EventType.WALLET_CREATED.value: WalletCreated,
    EventType.WALLET_UPDATED.value: WalletUpdated,
    EventType.WALLET_BOUGHT_TOKEN.value: WalletBoughtToken,
    EventType.WALLET_SOLD_TOKEN.value: WalletSoldToken,
    EventType.LIQUIDITY_ADDED.value: LiquidityAdded,
    EventType.LIQUIDITY_REMOVED.value: LiquidityRemoved,
    EventType.ATTENTION_SPIKE.value: AttentionSpike,
    EventType.CLUSTER_DETECTED.value: ClusterDetected,
    EventType.PREDICTION_GENERATED.value: PredictionGenerated,
    EventType.BUY_SIGNAL_GENERATED.value: BuySignalGenerated,
    EventType.TRADE_EXECUTED.value: TradeExecuted,
}
