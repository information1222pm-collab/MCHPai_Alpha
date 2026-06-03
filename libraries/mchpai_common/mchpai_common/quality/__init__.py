"""Dataset quality & integrity — making the observatory's health observable.

This is verification, not generation: it does not add features, sciences, or
data. It answers the empirical question "does reality agree?" via pure,
deterministic checks (so they are unit-testable and trustworthy):

  integrity — slot gaps, duplicate births, sequence monotonicity, replay
              determinism, feature leakage (causality), online/offline parity.
  metrics   — coverage, null rates, label maturity, PSI drift.
  report    — a GREEN/YELLOW/RED rollup (DatasetQualityReport).

Run by ``scripts/validate_dataset.py`` against the live stores; surfaced at
``GET /quality``.
"""

from .integrity import (
    SequenceIntegrity,
    assert_causal,
    boundary_aligned,
    find_duplicate_births,
    find_slot_gaps,
    online_offline_divergence,
    replay_consistent,
    sequence_integrity,
    total_slot_gap,
)
from .metrics import coverage, feature_drift_psi, label_maturity, null_rate, psi
from .report import DatasetQualityReport, Status

__all__ = [
    "SequenceIntegrity",
    "assert_causal",
    "boundary_aligned",
    "find_duplicate_births",
    "find_slot_gaps",
    "online_offline_divergence",
    "replay_consistent",
    "sequence_integrity",
    "total_slot_gap",
    "coverage",
    "feature_drift_psi",
    "label_maturity",
    "null_rate",
    "psi",
    "DatasetQualityReport",
    "Status",
]
