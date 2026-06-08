"""SyntheticSource is a deterministic chaos generator: same seed → same stream,
and its adversarial content (oversells, dust, out-of-order time) must flow
through the log and projector without crashing or losing determinism."""

from __future__ import annotations

from wis.domain.identifiers import WalletAddress
from wis.eventsourcing.replay import ReplayEngine
from wis.eventsourcing.store import InMemoryEventStore
from wis.projections.wallet_projector import WalletProjector
from wis.sources import SyntheticConfig, SyntheticSource, collect, pump


def test_same_seed_same_stream() -> None:
    cfg = SyntheticConfig(seed=42, n_events=300, fault_rate=0.2)
    a = [e.payload for e in collect(SyntheticSource(cfg))]
    b = [e.payload for e in collect(SyntheticSource(cfg))]
    assert a == b and len(a) > 0


def test_different_seed_different_stream() -> None:
    a = [e.payload for e in collect(SyntheticSource(SyntheticConfig(seed=1, n_events=100)))]
    b = [e.payload for e in collect(SyntheticSource(SyntheticConfig(seed=2, n_events=100)))]
    assert a != b


def test_faults_flow_through_without_crashing() -> None:
    cfg = SyntheticConfig(seed=7, n_wallets=4, n_tokens=4, n_events=500, fault_rate=0.4)
    store = InMemoryEventStore()
    pump(SyntheticSource(cfg), store)

    world = ReplayEngine(store, WalletProjector()).run()
    # The adversarial stream produces oversells somewhere — recorded, not fatal.
    total_oversold = sum(ws.ledger.oversold_events for ws in world.wallets.values())
    assert total_oversold > 0

    # Frames still compute on adversarial data (no exceptions, bounded values).
    for ws in world.wallets.values():
        frame = ws.frame(prices=world.prices)
        assert frame.sample_size >= 0


def test_replay_of_synthetic_is_deterministic() -> None:
    cfg = SyntheticConfig(seed=99, n_events=400, fault_rate=0.3)
    from wis.conformance import wallet_world_digest

    def digest() -> str:
        store = InMemoryEventStore()
        pump(SyntheticSource(cfg), store)
        return wallet_world_digest(ReplayEngine(store, WalletProjector()).run())

    assert digest() == digest()
    # And at least one wallet actually traded.
    store = InMemoryEventStore()
    pump(SyntheticSource(cfg), store)
    world = ReplayEngine(store, WalletProjector()).run()
    assert any(ws.closed_trade_count > 0 for ws in world.wallets.values())
    assert WalletAddress("w0") in world.wallets
