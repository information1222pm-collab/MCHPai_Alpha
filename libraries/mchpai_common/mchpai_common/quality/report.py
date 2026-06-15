"""DatasetQualityReport — the GREEN/YELLOW/RED rollup surfaced at /quality."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class Status(str, Enum):
    green = "GREEN"
    yellow = "YELLOW"
    red = "RED"


@dataclass
class DatasetQualityReport:
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # hard integrity (any failure ⇒ RED, blocks milestones)
    duplicate_births: int = 0
    replay_deterministic: bool = True
    feature_leakage: bool = False          # True ⇒ leakage detected ⇒ RED
    online_offline_consistent: bool = True
    snapshot_skew: int = 0                  # count of (mint,window) with bad seq/ts

    # coverage / soft (drive YELLOW)
    total_slot_gap: int = 0
    slot_gap_backlog_growing: bool = False
    event_completeness: float = 1.0
    snapshot_coverage: float = 1.0
    label_maturity: float = 0.0
    max_feature_null_rate: float = 0.0
    max_feature_psi: float = 0.0

    details: dict = field(default_factory=dict)

    # thresholds
    NULL_RATE_WARN: float = 0.6
    PSI_WARN: float = 0.25
    COMPLETENESS_WARN: float = 0.95

    def status(self) -> Status:
        # RED: any hard-integrity violation
        if (
            self.duplicate_births > 0
            or not self.replay_deterministic
            or self.feature_leakage
            or not self.online_offline_consistent
            or self.snapshot_skew > 0
        ):
            return Status.red
        # YELLOW: soft concerns
        if (
            self.slot_gap_backlog_growing
            or self.event_completeness < self.COMPLETENESS_WARN
            or self.snapshot_coverage < self.COMPLETENESS_WARN
            or self.max_feature_null_rate > self.NULL_RATE_WARN
            or self.max_feature_psi > self.PSI_WARN
        ):
            return Status.yellow
        return Status.green

    def to_dict(self) -> dict:
        d = {
            "generated_at": self.generated_at,
            "status": self.status().value,
            "hard": {
                "duplicate_births": self.duplicate_births,
                "replay_deterministic": self.replay_deterministic,
                "feature_leakage": self.feature_leakage,
                "online_offline_consistent": self.online_offline_consistent,
                "snapshot_skew": self.snapshot_skew,
            },
            "soft": {
                "total_slot_gap": self.total_slot_gap,
                "slot_gap_backlog_growing": self.slot_gap_backlog_growing,
                "event_completeness": self.event_completeness,
                "snapshot_coverage": self.snapshot_coverage,
                "label_maturity": self.label_maturity,
                "max_feature_null_rate": self.max_feature_null_rate,
                "max_feature_psi": self.max_feature_psi,
            },
            "details": self.details,
        }
        return d
