"""Oracle conformance — the contract every EventStore must satisfy.

The :class:`~wis.eventsourcing.store.InMemoryEventStore` is the *oracle*: the
reference definition of correct behavior. A persistence adapter is correct if
and only if, given the same log, it reproduces **bit-identical** projected
state. This module provides:

* deterministic *digests* of a projected ``wallet_state(t)`` / ``graph(t)`` —
  exact fingerprints (rational money rendered losslessly) so two worlds can be
  compared for true equality, not approximate equality;
* :func:`assert_eventstore_conforms`, a store-agnostic check that an adapter
  matches the oracle on sequencing, ordering, point-in-time reads, round-trip
  fidelity, and — the sacred one — replay determinism.

Adapters (SQLite, PostgreSQL, NATS+MinIO, …) all run through this same harness.
Replay determinism is sacred; point-in-time correctness is sacred; this module
is where those vows are enforced rather than merely asserted in prose.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from collections.abc import Sequence as Seq
from fractions import Fraction
from typing import Any

from wis.domain.events import DomainEvent
from wis.domain.time import Nanos, Sequence
from wis.eventsourcing.codec import decode_stored, encode_stored
from wis.eventsourcing.replay import ReplayEngine
from wis.eventsourcing.store import EventStore
from wis.projections.graph_projector import GraphProjector, GraphWorld
from wis.projections.wallet_projector import WalletProjector, WalletWorld


def canonical_event_log() -> list[tuple[DomainEvent, Nanos]]:
    """A representative log exercising every ingestion event type and the tricky
    ledger paths (multi-lot FIFO, partial fills, an oversell). Shared by every
    adapter's conformance test so they are all judged against the same reality.
    """
    from wis.domain.events import (
        TokenPriceObserved,
        WalletBoughtToken,
        WalletCreated,
        WalletFunded,
        WalletSoldToken,
        WalletUpdated,
    )
    from wis.domain.identifiers import TokenMint, WalletAddress
    from wis.domain.money import Amount

    def sol(x: float) -> Amount:
        return Amount(raw=int(round(x * 1e9)), decimals=9)

    def tok(x: float) -> Amount:
        return Amount(raw=int(round(x * 1e6)), decimals=6)

    day = 86_400_000_000_000
    log: list[tuple[DomainEvent, Nanos]] = []
    t = day

    def add(ev: DomainEvent) -> None:
        nonlocal t
        log.append((ev, Nanos(t + 1_000_000_000)))  # ingestion lags event by 1s
        t += 3600_000_000_000  # advance 1h

    a, b = WalletAddress("alpha"), WalletAddress("bravo")
    gem = TokenMint("GEM")
    add(WalletCreated(occurred_at=Nanos(t), wallet=a))
    add(WalletCreated(occurred_at=Nanos(t), wallet=b, funded_by=a))
    add(WalletFunded(occurred_at=Nanos(t), source=a, target=b, amount=sol(5.0)))
    add(TokenPriceObserved(occurred_at=Nanos(t), token=gem, price_quote_per_base=sol(1.0)))
    add(WalletBoughtToken(occurred_at=Nanos(t), wallet=a, token=gem, base=tok(1000), quote=sol(1.0)))
    add(WalletBoughtToken(occurred_at=Nanos(t), wallet=a, token=gem, base=tok(500), quote=sol(0.75)))
    add(WalletBoughtToken(occurred_at=Nanos(t), wallet=b, token=gem, base=tok(300), quote=sol(0.9)))
    add(TokenPriceObserved(occurred_at=Nanos(t), token=gem, price_quote_per_base=sol(3.0)))
    add(WalletSoldToken(occurred_at=Nanos(t), wallet=a, token=gem, base=tok(1200), quote=sol(3.6)))  # spans lots
    add(WalletSoldToken(occurred_at=Nanos(t), wallet=b, token=gem, base=tok(900), quote=sol(2.7)))  # oversell
    add(WalletUpdated(occurred_at=Nanos(t), wallet=a, attributes={"label": "scout", "tier": "1"}))
    return log


def _frac(x: Fraction) -> str:
    """Lossless rational rendering: ``numerator/denominator``."""
    return f"{x.numerator}/{x.denominator}"


def wallet_world_digest(world: WalletWorld) -> str:
    """A canonical, exact fingerprint of every wallet's full ledger state."""
    wallets: list[dict[str, Any]] = []
    for address in sorted(world.wallets, key=lambda w: w.value):
        ws = world.wallets[address]
        wallets.append(
            {
                "address": address.value,
                "created_at": int(ws.created_at),
                "funded_by": ws.funded_by.value if ws.funded_by else None,
                "last_sequence": int(ws.last_sequence),
                "last_event_time": int(ws.last_event_time),
                "buy_count": ws.buy_count,
                "sell_count": ws.sell_count,
                "oversold": ws.ledger.oversold_events,
                "attributes": dict(sorted(ws.attributes.items())),
                "closed": [
                    {
                        "token": t.token.value,
                        "quote": t.quote,
                        "qty": _frac(t.qty),
                        "cost": _frac(t.cost),
                        "proceeds": _frac(t.proceeds),
                        "entry_time": int(t.entry_time),
                        "exit_time": int(t.exit_time),
                        "entry_seq": int(t.entry_sequence),
                        "exit_seq": int(t.exit_sequence),
                    }
                    for t in ws.ledger.closed
                ],
                "open": [
                    {
                        "token": p.token.value,
                        "quote": p.quote,
                        "qty": _frac(p.qty),
                        "cost": _frac(p.cost),
                        "first_entry": int(p.first_entry_time),
                        "last_entry": int(p.last_entry_time),
                    }
                    for p in sorted(ws.open_positions(), key=lambda p: (p.token.value, p.quote))
                ],
            }
        )
    blob = json.dumps(wallets, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def graph_world_digest(world: GraphWorld) -> str:
    g = world.graph
    cobuy = {
        a.value: {b.value: _frac(Fraction(w).limit_denominator(10**9)) for b, w in sorted(nbrs.items(), key=lambda kv: kv[0].value)}
        for a, nbrs in sorted(g.cobuy.items(), key=lambda kv: kv[0].value)
    }
    funding = {
        s.value: sorted(t.value for t in targets)
        for s, targets in sorted(g.funding_out.items(), key=lambda kv: kv[0].value)
    }
    blob = json.dumps(
        {"nodes": sorted(n.value for n in g.nodes), "cobuy": cobuy, "funding": funding},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(blob.encode()).hexdigest()


def load_events(store: EventStore, events: Seq[tuple[DomainEvent, Nanos]]) -> None:
    """Append ``(payload, ingestion_time)`` pairs to a store, preserving order."""
    for payload, ingestion in events:
        store.append(payload, ingestion_time=ingestion)


def assert_eventstore_conforms(
    make_store: Callable[[], EventStore],
    events: Seq[tuple[DomainEvent, Nanos]],
) -> None:
    """Verify an adapter behaves identically to the in-memory oracle.

    ``make_store`` must return a *fresh, empty* store on each call. ``events`` is
    a script of ``(payload, ingestion_time)`` pairs to drive both stores.
    """
    from wis.eventsourcing.store import InMemoryEventStore

    oracle = InMemoryEventStore()
    candidate = make_store()
    load_events(oracle, events)
    load_events(candidate, events)

    # 1) Sequencing: gap-free, monotonic, equal heads.
    oracle_seqs = [e.sequence for e in oracle.read()]
    cand_seqs = [e.sequence for e in candidate.read()]
    assert oracle_seqs == cand_seqs == list(range(1, len(events) + 1)), "sequence mismatch"
    assert int(candidate.head) == int(oracle.head) == len(events), "head mismatch"

    # 2) Round-trip fidelity: every stored event decodes to an identical payload
    #    and identical envelope metadata.
    for o, c in zip(oracle.read(), candidate.read(), strict=True):
        assert c.payload == o.payload, f"payload differs at seq {o.sequence}"
        assert int(c.ingestion_time) == int(o.ingestion_time), "ingestion_time differs"
        assert c.event_id == o.event_id, "event_id differs"
        # The codec itself must be exact for this adapter's events.
        assert decode_stored(encode_stored(c)).payload == c.payload

    # 3) Read window semantics (after exclusive, up_to inclusive).
    if len(events) >= 3:
        mid_o = [int(e.sequence) for e in oracle.read(after=Sequence(1), up_to=Sequence(3))]
        mid_c = [int(e.sequence) for e in candidate.read(after=Sequence(1), up_to=Sequence(3))]
        assert mid_o == mid_c == [2, 3], "read window mismatch"

    # 4) Point-in-time reads: identical visibility under as_of.
    if events:
        cutoff = Nanos(sorted(int(i) for _, i in events)[len(events) // 2])
        as_of_o = [int(e.sequence) for e in oracle.read_as_of(cutoff)]
        as_of_c = [int(e.sequence) for e in candidate.read_as_of(cutoff)]
        assert as_of_o == as_of_c, "as_of visibility mismatch"

    # 5) THE SACRED CHECK — replay determinism. Both stores must fold into a
    #    bit-identical wallet_state(t) and graph(t).
    w_oracle = ReplayEngine(oracle, WalletProjector()).run()
    w_cand = ReplayEngine(candidate, WalletProjector()).run()
    assert wallet_world_digest(w_oracle) == wallet_world_digest(w_cand), "wallet replay diverged"

    g_oracle = ReplayEngine(oracle, GraphProjector()).run()
    g_cand = ReplayEngine(candidate, GraphProjector()).run()
    assert graph_world_digest(g_oracle) == graph_world_digest(g_cand), "graph replay diverged"
