"""Incremental creator state reducer — creator_state(t).

Creators evolve: a builder today can turn rugger tomorrow. We record the running
track record after each launch resolves, producing a ``creator_state(t)``
trajectory that later becomes creator embeddings.
"""

from __future__ import annotations

from datetime import datetime

from ..schemas.state import CreatorState


class CreatorStateReducer:
    def __init__(self, creator: str) -> None:
        self.creator = creator
        self._seq = 0
        self._launches = 0
        self._rugs = 0
        self._alive = 0
        self._best = 1.0
        self._volume = 0.0

    def on_launch(self, ts: datetime, *, volume_sol: float = 0.0) -> CreatorState:
        self._launches += 1
        self._alive += 1
        self._volume += volume_sol
        return self._emit(ts)

    def on_resolved(
        self, ts: datetime, *, rugged: bool, max_multiple: float = 1.0
    ) -> CreatorState:
        if rugged:
            self._rugs += 1
            self._alive = max(0, self._alive - 1)
        self._best = max(self._best, max_multiple)
        return self._emit(ts)

    def _emit(self, ts: datetime) -> CreatorState:
        rug_rate = self._rugs / self._launches if self._launches else 0.0
        self._seq += 1
        return CreatorState(
            creator=self.creator,
            ts=ts,
            seq=self._seq - 1,
            launches_so_far=self._launches,
            rugs_so_far=self._rugs,
            rug_rate=rug_rate,
            best_multiple_so_far=self._best,
            alive_count=self._alive,
            cumulative_volume_sol=self._volume,
        )
