"""Plain-dict serializers for the read models.

Kept dependency-free (no pydantic) so the core stays importable everywhere and
the wire format is a transparent function of the dataclasses. The API layer adds
HTTP; these add shape.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from wis.app.observatory import WalletReport
from wis.domain.graph.metrics import GraphSummary, GraphWalletMetrics
from wis.domain.identifiers import WalletAddress
from wis.domain.wallet.state import WalletFrame
from wis.scoring.scores import WalletScores


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (WalletAddress,)):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {k: _plain(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(_plain(k)): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_plain(v) for v in value]
    return value


def frame_to_dict(frame: WalletFrame) -> dict[str, Any]:
    return {
        "address": frame.address.value,
        "as_of_sequence": int(frame.as_of_sequence),
        "as_of_time": int(frame.as_of_time),
        "sample_size": frame.sample_size,
        "performance": _plain(frame.performance),
        "timing": _plain(frame.timing),
        "conviction": _plain(frame.conviction),
        "risk": _plain(frame.risk),
        "dna": {
            "strengths": [t.value for t in frame.dna.strengths],
            "weaknesses": [t.value for t in frame.dna.weaknesses],
            "tendencies": [t.value for t in frame.dna.tendencies],
            "evidence": frame.dna.evidence,
            "summary": frame.dna.summary(),
        },
    }


def scores_to_dict(scores: WalletScores) -> dict[str, Any]:
    return _plain(scores)


def graph_metrics_to_dict(g: GraphWalletMetrics | None) -> dict[str, Any] | None:
    return _plain(g) if g is not None else None


def report_to_dict(report: WalletReport) -> dict[str, Any]:
    return {
        "frame": frame_to_dict(report.frame),
        "scores": scores_to_dict(report.scores),
        "graph": graph_metrics_to_dict(report.graph),
        "features": {k: v.value for k, v in report.features.values.items()},
    }


def graph_summary_to_dict(s: GraphSummary) -> dict[str, Any]:
    return _plain(s)
