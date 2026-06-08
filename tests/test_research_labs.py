"""The research labs are pure analyses over observed reality — they return data,
never orders. We check the flagship lenses produce coherent output."""

from __future__ import annotations

from tests.conftest import Scenario
from wis.app.observatory import Observatory
from wis.domain.identifiers import WalletAddress
from wis.eventsourcing.store import InMemoryEventStore
from wis.research import behavior_lab, sequence_lab, wallet_alpha_lab


def _obs() -> Observatory:
    store = InMemoryEventStore()
    s = Scenario(store)
    s.created("pro")
    s.created("noob")
    for i in range(30):
        tok = f"P{i}"
        s.price(tok, 1.0)
        s.buy("pro", tok, base=100, quote=1.0)
        s.price(tok, 1.4)
        s.sell("pro", tok, base=100, quote=1.4)
    # noob loses repeatedly
    for i in range(30):
        tok = f"N{i}"
        s.price(tok, 1.0)
        s.buy("noob", tok, base=100, quote=1.0)
        s.price(tok, 0.5)
        s.sell("noob", tok, base=100, quote=0.5)
    return Observatory(store)


def test_leaderboard_ranks_pro_above_noob() -> None:
    board = wallet_alpha_lab.leaderboard(_obs(), min_confidence=0.3)
    addrs = [r.address for r in board]
    assert addrs.index(WalletAddress("pro")) < addrs.index(WalletAddress("noob"))


def test_behavior_trait_frequencies_nonempty() -> None:
    freqs = behavior_lab.trait_frequencies(_obs())
    assert sum(freqs.values()) > 0


def test_sequence_lab_shows_evolution() -> None:
    timeline = sequence_lab.wallet_timeline(_obs(), WalletAddress("pro"))
    # The wallet is a movie: many frames, confidence rising over time.
    assert len(timeline) > 5
    assert timeline[-1].confidence > timeline[0].confidence
