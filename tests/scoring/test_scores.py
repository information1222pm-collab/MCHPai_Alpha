"""Scores must express truth, not hype: thin samples are shrunk toward neutral,
and absent evidence yields ``None`` rather than a fabricated number."""

from __future__ import annotations

from tests.conftest import Scenario
from wis.domain.identifiers import WalletAddress
from wis.eventsourcing.replay import ReplayEngine
from wis.eventsourcing.store import InMemoryEventStore
from wis.projections.wallet_projector import WalletProjector
from wis.scoring.scores import score_wallet


def _frame_for(store: InMemoryEventStore, addr: str):
    world = ReplayEngine(store, WalletProjector()).run()
    ws = world.wallets[WalletAddress(addr)]
    return ws.frame(prices=world.prices)


def test_thin_sample_is_shrunk_toward_neutral() -> None:
    store = InMemoryEventStore()
    s = Scenario(store)
    s.created("lucky")
    s.price("X", 1.0)
    s.buy("lucky", "X", base=100, quote=1.0)
    s.price("X", 100.0)
    s.sell("lucky", "X", base=100, quote=100.0)  # one 100x trade
    scores = score_wallet(_frame_for(store, "lucky"))
    # One spectacular trade must NOT yield near-certain alpha.
    assert scores.confidence < 0.1
    assert scores.wallet_alpha_score is not None
    assert scores.wallet_alpha_score < 0.65


def test_more_evidence_raises_confidence() -> None:
    store = InMemoryEventStore()
    s = Scenario(store)
    s.created("grinder")
    for i in range(40):
        tok = f"T{i}"
        s.price(tok, 1.0)
        s.buy("grinder", tok, base=100, quote=1.0)
        s.price(tok, 1.5)
        s.sell("grinder", tok, base=100, quote=1.5)
    scores = score_wallet(_frame_for(store, "grinder"))
    assert scores.confidence > 0.6
    # Consistent winner with real evidence should read clearly above neutral.
    assert scores.wallet_alpha_score is not None
    assert scores.wallet_alpha_score > 0.6


def test_no_graph_means_no_social_scores() -> None:
    store = InMemoryEventStore()
    Scenario(store).created("solo")
    world = ReplayEngine(store, WalletProjector()).run()
    ws = world.wallets[WalletAddress("solo")]
    scores = score_wallet(ws.frame(prices=world.prices))
    assert scores.influence_score is None
    assert scores.cluster_score is None
