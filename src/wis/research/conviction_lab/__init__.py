"""conviction_lab — sizing, concentration, and the diamond-hands cohort."""

from __future__ import annotations

from dataclasses import dataclass

from wis.app.observatory import Observatory
from wis.domain.identifiers import WalletAddress


@dataclass(frozen=True, slots=True)
class ConvictionRow:
    address: WalletAddress
    diamond_hands: float | None
    concentration: float
    distinct_tokens: int
    avg_position_size: float | None


def diamond_hands_cohort(obs: Observatory, *, threshold: float = 0.6) -> list[ConvictionRow]:
    """Wallets whose holding behavior crosses the diamond-hands threshold,
    ranked by conviction."""
    rows: list[ConvictionRow] = []
    for address in obs.list_wallets():
        frame = obs.wallet_frame(address)
        if frame is None:
            continue
        c = frame.conviction
        if c.diamond_hands_score is not None and c.diamond_hands_score >= threshold:
            rows.append(
                ConvictionRow(
                    address=address,
                    diamond_hands=c.diamond_hands_score,
                    concentration=c.position_concentration,
                    distinct_tokens=c.distinct_tokens,
                    avg_position_size=c.average_position_size,
                )
            )
    rows.sort(key=lambda r: r.diamond_hands or 0.0, reverse=True)
    return rows
