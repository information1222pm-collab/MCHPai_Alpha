"""The event store and replay engine are the reproducibility foundation, so we
hold them to the strictest contracts: monotonic sequencing, point-in-time
visibility, and bit-identical replay."""

from __future__ import annotations

from tests.conftest import Scenario
from wis.domain.time import Nanos
from wis.eventsourcing.replay import ReplayEngine
from wis.eventsourcing.store import InMemoryEventStore
from wis.projections.wallet_projector import WalletProjector


def _build() -> InMemoryEventStore:
    store = InMemoryEventStore()
    s = Scenario(store)
    s.created("alpha")
    s.price("BONK", 1.0)
    s.buy("alpha", "BONK", base=1000, quote=1.0)
    s.price("BONK", 3.0)
    s.sell("alpha", "BONK", base=1000, quote=3.0)
    return store


def test_sequences_are_gapfree_and_monotonic() -> None:
    store = _build()
    seqs = [e.sequence for e in store.read()]
    assert seqs == list(range(1, len(seqs) + 1))
    assert store.head == len(seqs)


def test_read_window_is_inclusive_exclusive() -> None:
    store = _build()
    middle = [e.sequence for e in store.read(after=1, up_to=3)]
    assert middle == [2, 3]


def test_replay_is_deterministic() -> None:
    store = _build()
    engine = ReplayEngine(store, WalletProjector())
    a = engine.run()
    b = engine.run()
    # Two independent replays must agree on the realised pnl, exactly.
    from wis.domain.identifiers import WalletAddress

    ra = a.wallets[WalletAddress("alpha")].ledger.closed
    rb = b.wallets[WalletAddress("alpha")].ledger.closed
    assert [t.pnl for t in ra] == [t.pnl for t in rb]
    assert ra[0].pnl == 2  # bought for 1 SOL, sold for 3 SOL


def test_as_of_is_point_in_time() -> None:
    store = _build()
    engine = ReplayEngine(store, WalletProjector())
    # As of just after the buy's ingestion but before the sell, no closed trades.
    events = list(store.read())
    buy = next(e for e in events if e.event_type == "WalletBoughtToken")
    sell = next(e for e in events if e.event_type == "WalletSoldToken")
    as_of = Nanos((buy.ingestion_time + sell.ingestion_time) // 2)
    world = engine.run(as_of=as_of)
    from wis.domain.identifiers import WalletAddress

    ws = world.wallets[WalletAddress("alpha")]
    assert ws.closed_trade_count == 0
    assert len(ws.open_positions()) == 1
