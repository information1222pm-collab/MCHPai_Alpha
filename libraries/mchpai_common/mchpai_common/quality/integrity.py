"""Hard integrity checks. A failure here is at least S2 — corrupt data is worse
than no data."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any


# ---- slot gaps -------------------------------------------------------------
def find_slot_gaps(slots: Sequence[int]) -> list[tuple[int, int]]:
    """Return (start, end) inclusive ranges of missing slots between observations."""
    uniq = sorted(set(int(s) for s in slots))
    gaps: list[tuple[int, int]] = []
    for a, b in zip(uniq, uniq[1:]):
        if b - a > 1:
            gaps.append((a + 1, b - 1))
    return gaps


def total_slot_gap(slots: Sequence[int]) -> int:
    return sum(end - start + 1 for start, end in find_slot_gaps(slots))


# ---- duplicate births (must be zero) --------------------------------------
def find_duplicate_births(mints: Sequence[str]) -> list[str]:
    return [m for m, c in Counter(mints).items() if c > 1]


# ---- snapshot sequence integrity ------------------------------------------
@dataclass
class SequenceIntegrity:
    monotonic: bool          # strictly increasing
    duplicates: list[int]
    gaps: list[tuple[int, int]]

    @property
    def ok(self) -> bool:
        return self.monotonic and not self.duplicates and not self.gaps


def sequence_integrity(seqs: Sequence[int]) -> SequenceIntegrity:
    """Per-(mint,window) seq must be strictly increasing with no gaps/dupes."""
    dupes = [s for s, c in Counter(seqs).items() if c > 1]
    monotonic = all(b > a for a, b in zip(seqs, seqs[1:]))
    gaps = []
    for a, b in zip(sorted(set(seqs)), sorted(set(seqs))[1:]):
        if b - a > 1:
            gaps.append((a + 1, b - 1))
    return SequenceIntegrity(monotonic=monotonic, duplicates=sorted(dupes), gaps=gaps)


def boundary_aligned(ts_epoch_seconds: float, window_seconds: int) -> bool:
    """Snapshot close times must land on window boundaries (time-sync check)."""
    return abs(round(ts_epoch_seconds) % window_seconds) == 0


# ---- replay determinism ----------------------------------------------------
def replay_consistent(
    events: list[Any],
    build_reducer: Callable[[], Any],
    apply: Callable[[Any, Any], Any],
) -> bool:
    """Re-run pure reducers over the same ordered events; outputs must match.

    ``apply(reducer, event)`` returns a state object exposing ``model_dump()``
    (pydantic) or being directly comparable. Divergence ⇒ non-deterministic
    derivation, which poisons every downstream dataset and model.
    """

    def run() -> list:
        r = build_reducer()
        out = []
        for e in events:
            s = apply(r, e)
            out.append(s.model_dump() if hasattr(s, "model_dump") else s)
        return out

    return run() == run()


# ---- feature leakage (causality) ------------------------------------------
def assert_causal(compiler, rows: list[dict], *, perturb_index: int | None = None) -> bool:
    """Verify the compiled catalog is causal: perturbing a *future* row must not
    change any past feature vector. Returns True if causal (no leakage)."""
    if len(rows) < 3:
        return True
    i = perturb_index if perturb_index is not None else len(rows) - 1
    base = compiler.compute_sequence(rows)

    perturbed = [dict(r) for r in rows]
    # blow up a numeric field in the future row
    for k, v in perturbed[i].items():
        if isinstance(v, (int, float)):
            perturbed[i][k] = float(v) * 1000.0 + 12345.0
    after = compiler.compute_sequence(perturbed)

    # every vector strictly before i must be identical
    return all(base[j] == after[j] for j in range(i))


# ---- online/offline consistency -------------------------------------------
def online_offline_divergence(online: dict[str, float], offline: dict[str, float]) -> dict[str, float]:
    """Per-feature absolute difference between the live and recomputed vectors."""
    keys = set(online) | set(offline)
    return {k: abs(float(online.get(k, 0.0)) - float(offline.get(k, 0.0))) for k in keys}


def max_divergence(online: dict[str, float], offline: dict[str, float]) -> float:
    d = online_offline_divergence(online, offline)
    return max(d.values()) if d else 0.0
