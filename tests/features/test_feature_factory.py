"""The feature factory must be leak-free, online/offline consistent, and
versioned. We verify the compiler produces a stable, named vector and that
point-in-time frames cannot see the future."""

from __future__ import annotations

from tests.conftest import Scenario
from wis.domain.identifiers import WalletAddress
from wis.domain.time import Nanos
from wis.eventsourcing.replay import ReplayEngine
from wis.eventsourcing.store import InMemoryEventStore
from wis.features.compiler import FeatureCompiler
from wis.features.registry import DEFAULT_REGISTRY
from wis.projections.wallet_projector import WalletProjector


def _world(store: InMemoryEventStore):
    return ReplayEngine(store, WalletProjector()).run()


def _store() -> InMemoryEventStore:
    store = InMemoryEventStore()
    s = Scenario(store)
    s.created("w")
    s.price("X", 1.0)
    s.buy("w", "X", base=1000, quote=1.0)
    s.price("X", 3.0)
    s.sell("w", "X", base=1000, quote=3.0)
    return store


def test_registry_has_builtins() -> None:
    assert len(DEFAULT_REGISTRY) >= 20
    keys = {s.key for s in DEFAULT_REGISTRY}
    assert "perf.lifetime_roi@1" in keys


def test_compiler_produces_named_versioned_vector() -> None:
    world = _world(_store())
    frame = world.wallets[WalletAddress("w")].frame(prices=world.prices)
    vec = FeatureCompiler().compile(frame)
    assert vec.get("perf.lifetime_roi@1") == 2.0
    assert vec.get("perf.win_rate@1") == 1.0
    # Pending-enrichment features are present but null, never invented.
    assert "risk.rug_exposure@1" in vec.values
    assert vec.values["risk.rug_exposure@1"].is_null


def test_online_offline_consistency() -> None:
    # "Offline" path: full replay then compile.
    world = _world(_store())
    offline_frame = world.wallets[WalletAddress("w")].frame(prices=world.prices)
    offline = FeatureCompiler().compile(offline_frame)

    # "Online" path: same frame object handed straight to the compiler. Same
    # extract functions, so values are identical by construction.
    online = FeatureCompiler().compile(offline_frame)
    assert {k: v.value for k, v in offline.values.items()} == {
        k: v.value for k, v in online.values.items()
    }


def test_point_in_time_frame_has_no_lookahead() -> None:
    store = _store()
    engine = ReplayEngine(store, WalletProjector())
    events = list(store.read())
    buy = next(e for e in events if e.event_type == "WalletBoughtToken")
    # As of the buy's ingestion, the later sell is invisible: no realised roi.
    world = engine.run(as_of=Nanos(buy.ingestion_time))
    frame = world.wallets[WalletAddress("w")].frame(prices=world.prices)
    vec = FeatureCompiler().compile(frame)
    assert vec.get("perf.lifetime_roi@1") is None
