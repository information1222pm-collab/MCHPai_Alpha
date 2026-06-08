"""The projection→storage mapping is verified against the oracle WITHOUT any
database: exactness and determinism are properties of the mapping itself, so the
DB adapters only have to move these rows faithfully."""

from __future__ import annotations

import json
from fractions import Fraction

from wis.conformance import canonical_event_log
from wis.eventsourcing.replay import ReplayEngine
from wis.eventsourcing.store import InMemoryEventStore
from wis.infra.projection_rows import (
    closed_trade_rows,
    exact_total_pnl,
    graph_edges,
    wallet_state_blobs,
)
from wis.projections.graph_projector import GraphProjector
from wis.projections.wallet_projector import WalletProjector


def _worlds():
    store = InMemoryEventStore()
    for payload, ingestion in canonical_event_log():
        store.append(payload, ingestion_time=ingestion)
    wallet_world = ReplayEngine(store, WalletProjector()).run()
    graph_world = ReplayEngine(store, GraphProjector()).run()
    return wallet_world, graph_world


def test_trade_rows_preserve_exact_pnl() -> None:
    wallet_world, _ = _worlds()
    rows = closed_trade_rows(wallet_world)
    # Oracle exact pnl straight from the ledger.
    oracle_pnl = sum(
        (t.pnl for ws in wallet_world.wallets.values() for t in ws.ledger.closed),
        Fraction(0),
    )
    assert exact_total_pnl(rows) == oracle_pnl


def test_trade_rows_are_deterministically_ordered() -> None:
    wallet_world, _ = _worlds()
    a = closed_trade_rows(wallet_world)
    b = closed_trade_rows(wallet_world)
    assert a == b
    seqs = [r.exit_sequence for r in a]
    assert seqs == sorted(seqs)


def test_wallet_state_blobs_are_canonical_json() -> None:
    wallet_world, _ = _worlds()
    blobs = wallet_state_blobs(wallet_world)
    assert blobs == wallet_state_blobs(wallet_world)  # deterministic
    alpha = json.loads(blobs["alpha"])
    assert alpha["address"] == "alpha"
    assert alpha["closed_trades"] >= 1
    # total_pnl is carried as exact rational parts, never a rounded float.
    assert isinstance(alpha["total_pnl"], list) and len(alpha["total_pnl"]) == 2


def test_graph_edges_dedup_cobuy_and_keep_funding_direction() -> None:
    _, graph_world = _worlds()
    edges = graph_edges(graph_world)
    funded = [e for e in edges if e.kind == "FUNDED"]
    cobuy = [e for e in edges if e.kind == "COBUY"]
    # alpha funded bravo (directed); recorded once in that direction.
    assert any(e.source == "alpha" and e.target == "bravo" for e in funded)
    # Co-buy pairs are undirected: each unordered pair appears at most once.
    pairs = [(e.source, e.target) for e in cobuy]
    assert len(pairs) == len(set(pairs))
    assert all(s < t for s, t in pairs)
