"""wallet_alpha_lab — ranking and distribution of wallet alpha.

Answers "who are the highest-quality participants, and how confident are we?"
Crucially it ranks on *truth-weighted* alpha (already confidence-shrunk), so a
wallet cannot top the board on a tiny lucky sample.
"""

from __future__ import annotations

from dataclasses import dataclass

from wis.app.observatory import Observatory
from wis.domain.identifiers import WalletAddress


@dataclass(frozen=True, slots=True)
class AlphaRanking:
    address: WalletAddress
    alpha_score: float | None
    confidence: float
    sample_size: int


def leaderboard(obs: Observatory, *, min_confidence: float = 0.0, limit: int | None = None) -> list[AlphaRanking]:
    """Wallets ranked by alpha, descending. ``min_confidence`` filters out
    wallets whose evidence is too thin to take seriously."""
    rows: list[AlphaRanking] = []
    for address in obs.list_wallets():
        report = obs.wallet_report(address)
        if report is None or report.scores.confidence < min_confidence:
            continue
        rows.append(
            AlphaRanking(
                address=address,
                alpha_score=report.scores.wallet_alpha_score,
                confidence=report.scores.confidence,
                sample_size=report.frame.sample_size,
            )
        )
    rows.sort(key=lambda r: (r.alpha_score is not None, r.alpha_score or 0.0), reverse=True)
    return rows[:limit] if limit is not None else rows


def alpha_distribution(obs: Observatory, *, buckets: int = 10) -> list[int]:
    """Histogram of alpha across the population — the shape of skill in the set."""
    hist = [0] * buckets
    for address in obs.list_wallets():
        report = obs.wallet_report(address)
        if report is None or report.scores.wallet_alpha_score is None:
            continue
        idx = min(buckets - 1, int(report.scores.wallet_alpha_score * buckets))
        hist[idx] += 1
    return hist
