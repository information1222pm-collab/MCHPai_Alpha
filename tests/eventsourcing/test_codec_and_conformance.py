"""The codec must round-trip every event exactly, and the conformance harness
must validate the in-memory oracle against itself (a sanity floor)."""

from __future__ import annotations

from wis.conformance import (
    assert_eventstore_conforms,
    canonical_event_log,
    wallet_world_digest,
)
from wis.eventsourcing.codec import decode_payload, decode_stored, encode_payload, encode_stored
from wis.eventsourcing.replay import ReplayEngine
from wis.eventsourcing.store import InMemoryEventStore
from wis.projections.wallet_projector import WalletProjector


def test_codec_round_trips_every_event_type() -> None:
    for payload, _ in canonical_event_log():
        assert decode_payload(encode_payload(payload)) == payload


def test_stored_envelope_round_trips() -> None:
    store = InMemoryEventStore()
    for payload, ingestion in canonical_event_log():
        store.append(payload, ingestion_time=ingestion)
    for stored in store.read():
        restored = decode_stored(encode_stored(stored))
        assert restored.payload == stored.payload
        assert restored.sequence == stored.sequence
        assert restored.ingestion_time == stored.ingestion_time
        assert restored.event_id == stored.event_id


def test_encoding_is_canonical_and_deterministic() -> None:
    from wis.eventsourcing.codec import dumps_payload

    payload = canonical_event_log()[4][0]  # a buy
    assert dumps_payload(payload) == dumps_payload(payload)


def test_in_memory_oracle_conforms_to_itself() -> None:
    assert_eventstore_conforms(InMemoryEventStore, canonical_event_log())


def test_digest_is_stable_across_replays() -> None:
    store = InMemoryEventStore()
    for payload, ingestion in canonical_event_log():
        store.append(payload, ingestion_time=ingestion)
    d1 = wallet_world_digest(ReplayEngine(store, WalletProjector()).run())
    d2 = wallet_world_digest(ReplayEngine(store, WalletProjector()).run())
    assert d1 == d2
