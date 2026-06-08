"""The Observatory composes the whole pipeline and can write its own conclusions
back into the log as replayable derived events."""

from __future__ import annotations

from tests.conftest import Scenario
from wis.app.observatory import Observatory
from wis.domain.identifiers import WalletAddress
from wis.domain.time import Nanos
from wis.eventsourcing.store import InMemoryEventStore


def _populated() -> Observatory:
    store = InMemoryEventStore()
    s = Scenario(store)
    for w in ["w1", "w2", "w3"]:
        s.created(w)
    # Three wallets co-buying the same token in a tight window -> a cluster.
    for tok in ["AAA", "BBB"]:
        s.price(tok, 1.0)
        for w in ["w1", "w2", "w3"]:
            s.buy(w, tok, base=100, quote=1.0, advance=60_000_000_000)
        s.price(tok, 2.0)
        for w in ["w1", "w2", "w3"]:
            s.sell(w, tok, base=100, quote=2.0, advance=60_000_000_000)
    return Observatory(store)


def test_wallet_report_is_complete() -> None:
    obs = _populated()
    report = obs.wallet_report(WalletAddress("w1"))
    assert report is not None
    assert report.frame.performance.lifetime_roi == 1.0
    assert report.scores.wallet_alpha_score is not None
    assert report.graph is not None  # co-buyers appear in the graph
    assert report.features.get("perf.win_rate@1") == 1.0


def test_unknown_wallet_returns_none() -> None:
    obs = _populated()
    assert obs.wallet_report(WalletAddress("nope")) is None


def test_clusters_group_cobuyers() -> None:
    obs = _populated()
    clusters = obs.clusters()
    # All three co-buyers should land in one community.
    members = [m for ms in clusters.values() for m in ms]
    assert WalletAddress("w1") in members
    assert any(len(ms) == 3 for ms in clusters.values())


def test_emit_intelligence_appends_derived_events() -> None:
    obs = _populated()
    before = int(obs.store.head)
    emitted = obs.emit_intelligence(at=Nanos(10**18))
    after = int(obs.store.head)
    assert after > before
    types = {e.event_type for e in emitted}
    assert "WalletStateUpdated" in types
    assert "WalletProfileGenerated" in types
    assert "GraphUpdated" in types
    # The conclusions are now part of the replayable log.
    assert after == before + len(emitted)
