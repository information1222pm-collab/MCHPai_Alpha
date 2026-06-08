"""sequence_lab — the wallet as a movie, frame by frame.

The flagship demonstration of the system's core belief: *wallets are movies, not
snapshots*. This lab replays the log and emits a wallet's intelligence frame at
each step where its state advanced, so you can watch its alpha, DNA and metrics
*evolve* — and detect the moment a participant's character changes.
"""

from __future__ import annotations

from dataclasses import dataclass

from wis.app.observatory import Observatory
from wis.domain.identifiers import WalletAddress
from wis.domain.time import Nanos, Sequence
from wis.eventsourcing.replay import ReplayEngine
from wis.projections.wallet_projector import WalletProjector
from wis.scoring.scores import score_wallet


@dataclass(frozen=True, slots=True)
class TimelineFrame:
    sequence: Sequence
    event_time: Nanos
    closed_trades: int
    alpha_score: float | None
    confidence: float
    dna_summary: str


def wallet_timeline(obs: Observatory, address: WalletAddress) -> list[TimelineFrame]:
    """Every frame of a wallet's evolution, in order. One entry per event that
    advanced this wallet's state."""
    engine = ReplayEngine(obs.store, WalletProjector())
    timeline: list[TimelineFrame] = []
    last_seq = -1
    for _event, world in engine.trace():
        ws = world.get(address)
        if ws is None or int(ws.last_sequence) == last_seq:
            continue
        last_seq = int(ws.last_sequence)
        frame = ws.frame(prices=world.prices)
        scores = score_wallet(frame)
        timeline.append(
            TimelineFrame(
                sequence=ws.last_sequence,
                event_time=ws.last_event_time,
                closed_trades=frame.sample_size,
                alpha_score=scores.wallet_alpha_score,
                confidence=scores.confidence,
                dna_summary=frame.dna.summary(),
            )
        )
    return timeline


def character_changes(obs: Observatory, address: WalletAddress) -> list[TimelineFrame]:
    """Frames where the wallet's DNA summary changed — the plot points of its
    story."""
    timeline = wallet_timeline(obs, address)
    changes: list[TimelineFrame] = []
    prev: str | None = None
    for frame in timeline:
        if frame.dna_summary != prev:
            changes.append(frame)
            prev = frame.dna_summary
    return changes
