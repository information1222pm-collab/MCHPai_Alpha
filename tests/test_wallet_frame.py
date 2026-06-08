"""End-to-end: events fold into a wallet frame with sound, derived metrics."""

from __future__ import annotations

from tests.conftest import Scenario
from wis.domain.identifiers import WalletAddress
from wis.domain.wallet.dna import Trait
from wis.eventsourcing.replay import ReplayEngine
from wis.eventsourcing.store import InMemoryEventStore
from wis.projections.wallet_projector import WalletProjector


def _profitable_patient_wallet() -> InMemoryEventStore:
    store = InMemoryEventStore()
    s = Scenario(store)
    s.created("whale")
    for tok, entry, exit_ in [("AAA", 1.0, 3.0), ("BBB", 2.0, 5.0), ("CCC", 1.0, 4.0)]:
        s.price(tok, entry)
        s.buy("whale", tok, base=1000, quote=entry)
        s.price(tok, exit_)
        s.sell("whale", tok, base=1000, quote=exit_)
    return store


def _frame():
    store = _profitable_patient_wallet()
    world = ReplayEngine(store, WalletProjector()).run()
    ws = world.wallets[WalletAddress("whale")]
    return ws.frame(prices=world.prices)


def test_performance_is_computed_exactly() -> None:
    f = _frame()
    p = f.performance
    # Costs 1+2+1=4, proceeds 3+5+4=12, pnl 8 -> ROI 200%.
    assert p.lifetime_roi == 2.0
    assert p.win_rate == 1.0
    assert p.expectancy is not None and p.expectancy > 0
    assert p.max_drawdown == 0.0  # never went down


def test_timing_percentiles_present_with_price_context() -> None:
    f = _frame()
    # Bought at the low print and sold at the high print of each token.
    assert f.timing.entry_percentile is not None
    assert f.timing.exit_percentile is not None
    assert f.timing.entry_percentile <= f.timing.exit_percentile


def test_dna_names_strengths() -> None:
    f = _frame()
    assert Trait.PROFITABLE in f.dna.strengths
    # Evidence is attached and explainable.
    assert "profitable" in f.dna.evidence


def test_empty_wallet_frame_is_honest_about_absence() -> None:
    store = InMemoryEventStore()
    Scenario(store).created("ghost")
    world = ReplayEngine(store, WalletProjector()).run()
    ws = world.wallets[WalletAddress("ghost")]
    f = ws.frame(prices=world.prices)
    # No trades -> metrics are None, not fabricated zeros.
    assert f.performance.lifetime_roi is None
    assert f.risk.rug_exposure is None  # pending enrichment, always
