"""timing_lab — entry/exit timing and patience across the population."""

from __future__ import annotations

from dataclasses import dataclass

from wis.app.observatory import Observatory
from wis.domain import stats


@dataclass(frozen=True, slots=True)
class TimingProfile:
    median_entry_percentile: float | None
    median_exit_percentile: float | None
    median_patience: float | None
    population: int


def population_timing(obs: Observatory) -> TimingProfile:
    """Aggregate timing behavior over all wallets with observable timing."""
    entries, exits, patience = [], [], []
    for address in obs.list_wallets():
        frame = obs.wallet_frame(address)
        if frame is None:
            continue
        t = frame.timing
        if t.entry_percentile is not None:
            entries.append(t.entry_percentile)
        if t.exit_percentile is not None:
            exits.append(t.exit_percentile)
        if t.patience_score is not None:
            patience.append(t.patience_score)
    return TimingProfile(
        median_entry_percentile=stats.median(entries) if entries else None,
        median_exit_percentile=stats.median(exits) if exits else None,
        median_patience=stats.median(patience) if patience else None,
        population=len(obs.list_wallets()),
    )
