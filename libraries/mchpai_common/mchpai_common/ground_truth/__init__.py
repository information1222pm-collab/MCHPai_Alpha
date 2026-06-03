"""Ground-truth generation.

Turns a token's *completed* snapshot sequence into frozen labels — the multiples
it achieved within each horizon and its terminal outcome (rugged / survived /
viral). These are the targets for every supervised model (buy_probability,
rug_probability, survival_probability, Nx_probability).

This runs strictly *after the fact*: a label is only `is_final` once the 7d
window closes, which prevents look-ahead leakage from contaminating training.
"""

from .labels import compute_ground_truth, SnapshotPoint

__all__ = ["compute_ground_truth", "SnapshotPoint"]
