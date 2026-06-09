"""The ratings pipeline — sources → wallet_state(t) → ratings → store → leaderboard.

The same flow at any scale: ingest observed events (from any Source) into a log,
project ``wallet_state(t)``, rate every wallet, and upsert into a RatingStore.
Here it runs on a few thousand wallets with SQLite; on real infrastructure the
store becomes PostgreSQL/ClickHouse and the source becomes the live feed —
nothing else changes.
"""

from __future__ import annotations

from collections.abc import Iterable

from wis.eventsourcing.replay import ReplayEngine
from wis.eventsourcing.store import EventStore, InMemoryEventStore
from wis.projections.wallet_projector import WalletProjector, WalletWorld
from wis.ratings.model import WalletRating
from wis.ratings.rater import rate_world
from wis.ratings.store import RatingStore, SqliteRatingStore
from wis.sources.base import Source, pump


def world_from_sources(sources: Iterable[Source], *, store: EventStore | None = None) -> WalletWorld:
    log = store if store is not None else InMemoryEventStore()
    for src in sources:
        pump(src, log)
    return ReplayEngine(log, WalletProjector()).run()


def rate_and_store(world: WalletWorld, store: RatingStore) -> list[WalletRating]:
    ratings = rate_world(world)
    store.upsert(ratings)
    return ratings


def rate_sources(sources: Iterable[Source], store: RatingStore | None = None) -> tuple[list[WalletRating], RatingStore]:
    """End-to-end convenience: observe → rate → store. Returns ratings + store."""
    rstore = store if store is not None else SqliteRatingStore()
    world = world_from_sources(sources)
    ratings = rate_and_store(world, rstore)
    return ratings, rstore
