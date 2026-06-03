"""Token trajectory builder — the TFT-ready view of a token's life.

Wraps an ordered snapshot sequence into a :class:`TokenTrajectory`, extracting the
ordered (seq, age, phase, price) skeleton and the set of phases observed. This is
the bridge from raw snapshots to the matrix form temporal models consume.
"""

from __future__ import annotations

from datetime import datetime

from ..schemas.snapshot import TokenSnapshot
from ..schemas.state import TokenTrajectory


def build_trajectory(mint: str, birth_ts: datetime, snaps: list[TokenSnapshot]) -> TokenTrajectory:
    ordered = sorted(snaps, key=lambda s: (s.age_seconds, s.seq))
    steps = [
        {
            "seq": s.seq,
            "age_seconds": s.age_seconds,
            "phase": s.phase.value if s.phase else None,
            "price_sol": s.price_sol,
        }
        for s in ordered
    ]
    phases_seen: list[str] = []
    for s in ordered:
        p = s.phase.value if s.phase else None
        if p and (not phases_seen or phases_seen[-1] != p):
            phases_seen.append(p)
    return TokenTrajectory(
        mint=mint, birth_ts=birth_ts, seq_len=len(ordered),
        phases_seen=phases_seen, steps=steps,
    )
