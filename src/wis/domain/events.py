"""Domain events — the atomic facts of the system.

Everything the Wallet Intelligence System knows is derived from an ordered log
of immutable events. There are two families:

* **Ingestion events** are facts observed from the world: a wallet appeared, a
  wallet was funded, a wallet bought or sold a token, a price was observed.
  These are *causes*.
* **Derived events** are conclusions the system itself emits as it reasons:
  ``wallet_state(t)`` advanced, an alpha score changed, a cluster was detected,
  the graph was recomputed, a DNA profile was generated. These let downstream
  consumers (research labs, the API, future ML training) subscribe to
  intelligence as it forms, and let us replay the *reasoning*, not just the raw
  data.

Events are frozen and carry an explicit ``event_version`` so the schema can
evolve over decades without breaking historical replay. The canonical event
names from the system charter are preserved verbatim
(:data:`EVENT_TYPE` of each class).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Literal

from wis.domain.identifiers import ClusterId, TokenMint, WalletAddress
from wis.domain.money import Amount
from wis.domain.time import Nanos

# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Base class for every fact in the log.

    ``occurred_at`` is the world (event) time. The store stamps ingestion time
    and global sequence when the event is appended; producers never set those.
    """

    EVENT_TYPE: ClassVar[str] = "DomainEvent"
    event_version: ClassVar[int] = 1

    occurred_at: Nanos


# ---------------------------------------------------------------------------
# Ingestion events (causes — observed from the world)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WalletCreated(DomainEvent):
    """The first moment we become aware a wallet exists. Birth of an entity."""

    EVENT_TYPE: ClassVar[str] = "WalletCreated"

    wallet: WalletAddress
    funded_by: WalletAddress | None = None


@dataclass(frozen=True, slots=True)
class WalletFunded(DomainEvent):
    """A funding flow from one wallet to another. The raw signal from which
    funding trees, shared-funding clusters and Sybil structures emerge."""

    EVENT_TYPE: ClassVar[str] = "WalletFunded"

    source: WalletAddress
    target: WalletAddress
    amount: Amount


@dataclass(frozen=True, slots=True)
class WalletBoughtToken(DomainEvent):
    """A wallet acquired ``base`` units of ``token`` by spending ``quote``.

    The implied entry price is ``quote / base`` (computed exactly downstream).
    ``quote`` is denominated in the common quote asset (e.g. SOL in lamports).
    """

    EVENT_TYPE: ClassVar[str] = "WalletBoughtToken"

    wallet: WalletAddress
    token: TokenMint
    base: Amount  # token units received
    quote: Amount  # quote units spent
    venue: str | None = None


@dataclass(frozen=True, slots=True)
class WalletSoldToken(DomainEvent):
    """A wallet disposed of ``base`` units of ``token`` for ``quote``."""

    EVENT_TYPE: ClassVar[str] = "WalletSoldToken"

    wallet: WalletAddress
    token: TokenMint
    base: Amount  # token units sold
    quote: Amount  # quote units received
    venue: str | None = None


@dataclass(frozen=True, slots=True)
class TokenPriceObserved(DomainEvent):
    """A market price for a token at a point in time. Provides the price context
    needed for *timing* intelligence (entry/exit percentile) without letting any
    projection peek at prices it could not have known at time t."""

    EVENT_TYPE: ClassVar[str] = "TokenPriceObserved"

    token: TokenMint
    price_quote_per_base: Amount  # quote units per 1 whole token


# ---------------------------------------------------------------------------
# Derived events (conclusions — emitted by the system's own reasoning)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WalletUpdated(DomainEvent):
    """A non-trade attribute of a wallet changed (labels, tags, metadata)."""

    EVENT_TYPE: ClassVar[str] = "WalletUpdated"

    wallet: WalletAddress
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WalletStateUpdated(DomainEvent):
    """``wallet_state(t)`` advanced. Carries the sequence of the last input
    event folded in, so the state version is fully reproducible by replay."""

    EVENT_TYPE: ClassVar[str] = "WalletStateUpdated"

    wallet: WalletAddress
    closed_trades: int
    open_positions: int


@dataclass(frozen=True, slots=True)
class WalletAlphaUpdated(DomainEvent):
    """A wallet's alpha (and component scores) were recomputed."""

    EVENT_TYPE: ClassVar[str] = "WalletAlphaUpdated"

    wallet: WalletAddress
    alpha_score: float


@dataclass(frozen=True, slots=True)
class ClusterDetected(DomainEvent):
    """A new community of related wallets emerged from the graph."""

    EVENT_TYPE: ClassVar[str] = "ClusterDetected"

    cluster: ClusterId
    members: tuple[WalletAddress, ...]
    method: Literal["louvain"] = "louvain"


@dataclass(frozen=True, slots=True)
class ClusterUpdated(DomainEvent):
    """An existing cluster's membership evolved. Clusters are movies."""

    EVENT_TYPE: ClassVar[str] = "ClusterUpdated"

    cluster: ClusterId
    members: tuple[WalletAddress, ...]
    joined: tuple[WalletAddress, ...] = ()
    left: tuple[WalletAddress, ...] = ()


@dataclass(frozen=True, slots=True)
class GraphUpdated(DomainEvent):
    """``graph(t)`` was recomputed. Carries summary metrics for cheap consumers
    that don't want to materialize the whole graph."""

    EVENT_TYPE: ClassVar[str] = "GraphUpdated"

    node_count: int
    edge_count: int
    density: float
    cluster_count: int


@dataclass(frozen=True, slots=True)
class WalletProfileGenerated(DomainEvent):
    """A human- and machine-readable Wallet DNA profile was produced."""

    EVENT_TYPE: ClassVar[str] = "WalletProfileGenerated"

    wallet: WalletAddress
    summary: str


# A registry mapping the canonical event name -> class, for (de)serialization
# of the persisted log. Decades-stable: new event types are appended, never
# renamed in place.
EVENT_REGISTRY: dict[str, type[DomainEvent]] = {
    cls.EVENT_TYPE: cls
    for cls in (
        WalletCreated,
        WalletFunded,
        WalletBoughtToken,
        WalletSoldToken,
        TokenPriceObserved,
        WalletUpdated,
        WalletStateUpdated,
        WalletAlphaUpdated,
        ClusterDetected,
        ClusterUpdated,
        GraphUpdated,
        WalletProfileGenerated,
    )
}
