"""Snapshot aggregation — turning the swap firehose into ordered time-series.

The :class:`WindowAggregator` buckets swaps into fixed windows (5s/15s/30s/60s)
and emits one :class:`TokenSnapshot` per closed bucket, carrying a monotonic
``seq`` and ``age_seconds`` so the result is a strictly ordered sequence — the
substrate future sequence models (TFT/GNN/RL) will consume.

:func:`classify_phase` labels each step of that sequence with a
:class:`LifecyclePhase` (birth → growth → viral → distribution → death).
"""

from .aggregator import WindowAggregator, MultiWindowAggregator
from .lifecycle import classify_phase, label_sequence

__all__ = [
    "WindowAggregator",
    "MultiWindowAggregator",
    "classify_phase",
    "label_sequence",
]
