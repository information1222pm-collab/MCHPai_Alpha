"""Battlefield — situational awareness & decision tempo (OODA).

Trading memecoins is adversarial and time-critical, like combat. We borrow the
military OODA loop (Observe-Orient-Decide-Act) and threat/kill-chain framing to
structure decisions and to reason about *who else is on the field* (competing
bots, snipers) and how fast we must move to win the engagement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class OODAStage(str, Enum):
    OBSERVE = "observe"     # ingest on-chain signals
    ORIENT = "orient"       # contextualize with profiles/graph/features
    DECIDE = "decide"       # prediction crosses thresholds
    ACT = "act"             # size + submit Jito bundle


@dataclass
class ThreatPicture:
    """A snapshot of the competitive field around an opportunity."""

    competing_snipers: int = 0
    block_congestion: float = 0.0       # 0..1
    our_latency_ms: float = 0.0
    estimated_enemy_latency_ms: float = 0.0
    tags: list[str] = field(default_factory=list)

    def time_advantage_ms(self) -> float:
        """Positive = we are faster than the field."""
        return self.estimated_enemy_latency_ms - self.our_latency_ms

    def engagement_favorable(self) -> bool:
        """Engage only if we are faster and the field isn't too crowded."""
        return self.time_advantage_ms() > 0 and self.competing_snipers < 8


def threat_level(picture: ThreatPicture) -> float:
    """0..100 threat score — higher means a harder, more contested entry."""
    score = 0.0
    score += min(60.0, picture.competing_snipers * 8.0)
    score += picture.block_congestion * 25.0
    if picture.time_advantage_ms() < 0:
        score += 15.0
    return min(100.0, score)
