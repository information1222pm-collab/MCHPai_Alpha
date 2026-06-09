"""Deterministic projection → storage mapping.

The derived stores (Redis hot state, ClickHouse analytics, Neo4j graph) persist
*views* of the projected world. This module computes those views as plain,
exact, ordered rows — with **no database dependency at all** — so the mapping
itself can be verified against the oracle in-process, and the database adapters
stay thin (they only move these rows in and out).

Money is carried as exact rational parts ``(numerator, denominator)`` plus a
float approximation: the rationals preserve truth for reconciliation, the float
serves analytical queries. We never round the thing of record.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction

from wis.projections.graph_projector import GraphWorld
from wis.projections.wallet_projector import WalletWorld


def frac_parts(x: Fraction) -> tuple[int, int]:
    return (x.numerator, x.denominator)


# ---------------------------------------------------------------------------
# Redis — latest wallet_state(t) summary per wallet (the hot online view)
# ---------------------------------------------------------------------------


def wallet_state_blobs(world: WalletWorld) -> dict[str, str]:
    """address -> canonical JSON summary, suitable for a Redis hash. Deterministic
    so the same world always yields the same blobs."""
    out: dict[str, str] = {}
    for address, ws in world.wallets.items():
        closed = ws.ledger.closed
        total_cost = sum((t.cost for t in closed), Fraction(0))
        total_pnl = sum((t.pnl for t in closed), Fraction(0))
        summary = {
            "address": address.value,
            "last_sequence": int(ws.last_sequence),
            "last_event_time": int(ws.last_event_time),
            "closed_trades": len(closed),
            "open_positions": len(ws.open_positions()),
            "buy_count": ws.buy_count,
            "sell_count": ws.sell_count,
            "total_cost": frac_parts(total_cost),
            "total_pnl": frac_parts(total_pnl),
        }
        out[address.value] = json.dumps(summary, sort_keys=True, separators=(",", ":"))
    return out


# ---------------------------------------------------------------------------
# ClickHouse — one row per closed trade (the analytical fact table)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TradeRow:
    wallet: str
    token: str
    quote: str
    qty_num: int
    qty_den: int
    cost_num: int
    cost_den: int
    proceeds_num: int
    proceeds_den: int
    pnl_float: float
    entry_time: int
    exit_time: int
    entry_sequence: int
    exit_sequence: int


def closed_trade_rows(world: WalletWorld) -> list[TradeRow]:
    """All closed trades across all wallets, ordered deterministically by exit
    sequence then wallet — exactness preserved via rational parts."""
    rows: list[TradeRow] = []
    for address, ws in world.wallets.items():
        for t in ws.ledger.closed:
            qn, qd = frac_parts(t.qty)
            cn, cd = frac_parts(t.cost)
            pn, pd = frac_parts(t.proceeds)
            rows.append(
                TradeRow(
                    wallet=address.value,
                    token=t.token.value,
                    quote=t.quote,
                    qty_num=qn,
                    qty_den=qd,
                    cost_num=cn,
                    cost_den=cd,
                    proceeds_num=pn,
                    proceeds_den=pd,
                    pnl_float=float(t.pnl),
                    entry_time=int(t.entry_time),
                    exit_time=int(t.exit_time),
                    entry_sequence=int(t.entry_sequence),
                    exit_sequence=int(t.exit_sequence),
                )
            )
    rows.sort(key=lambda r: (r.exit_sequence, r.wallet, r.token))
    return rows


def exact_total_pnl(rows: list[TradeRow]) -> Fraction:
    """Sum trade pnl back to an exact rational — the reconciliation anchor."""
    total = Fraction(0)
    for r in rows:
        total += Fraction(r.proceeds_num, r.proceeds_den) - Fraction(r.cost_num, r.cost_den)
    return total


# ---------------------------------------------------------------------------
# Neo4j — relationship edges (the graph view)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Edge:
    source: str
    target: str
    kind: str  # "FUNDED" | "COBUY"
    weight: float


def graph_edges(world: GraphWorld) -> list[Edge]:
    """Deterministically ordered edges. Co-buy edges are undirected, emitted once
    per unordered pair (source < target) to avoid double counting."""
    g = world.graph
    edges: list[Edge] = []
    for source, targets in g.funding_out.items():
        for target in targets:
            edges.append(Edge(source=source.value, target=target.value, kind="FUNDED", weight=1.0))
    seen: set[tuple[str, str]] = set()
    for a, nbrs in g.cobuy.items():
        for b, w in nbrs.items():
            lo, hi = sorted((a.value, b.value))
            if (lo, hi) in seen:
                continue
            seen.add((lo, hi))
            edges.append(Edge(source=lo, target=hi, kind="COBUY", weight=float(w)))
    edges.sort(key=lambda e: (e.kind, e.source, e.target))
    return edges
