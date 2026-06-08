"""The validation instruments must detect real structure and reject noise —
existence is judged by reproduction, not by a single fit."""

from __future__ import annotations

import numpy as np

from wis.research.taxonomy_validation_lab.stability import (
    adjusted_rand,
    bimodality,
    cluster_stabilities,
    consensus_matrix,
)


def test_bimodality_detects_two_modes() -> None:
    rng = np.random.default_rng(0)
    vals = np.concatenate([rng.normal(0.05, 0.03, 60).clip(0, 1),
                           rng.normal(0.95, 0.03, 60).clip(0, 1)])
    m = bimodality(vals.tolist())
    assert m.best_k == 2 and m.is_bimodal
    assert m.separation > 0.5


def test_bimodality_rejects_single_mode() -> None:
    rng = np.random.default_rng(1)
    vals = rng.normal(0.3, 0.05, 120).clip(0, 1)
    m = bimodality(vals.tolist())
    assert not m.is_bimodal  # one mode → no split


def test_consensus_stability_high_for_separated_blobs() -> None:
    rng = np.random.default_rng(2)
    a = rng.normal([-5, 0], 0.3, (40, 2))
    b = rng.normal([5, 0], 0.3, (40, 2))
    x = np.vstack([a, b])
    ref = [0] * 40 + [1] * 40
    cons = consensus_matrix(x, 2, n_boot=40, frac=0.8)
    stabs = cluster_stabilities(cons, ref)
    assert stabs[0] > 0.9 and stabs[1] > 0.9  # both blobs reproduce


def test_consensus_stability_low_for_uniform_noise() -> None:
    rng = np.random.default_rng(3)
    x = rng.uniform(-1, 1, (60, 2))  # no real structure
    cons = consensus_matrix(x, 4, n_boot=40, frac=0.8)
    # Impose an arbitrary 4-way split; with no structure it should not reproduce.
    ref = ([0, 1, 2, 3] * 15)[:60]
    stabs = cluster_stabilities(cons, ref)
    assert max(stabs.values()) < 0.6


def test_adjusted_rand() -> None:
    assert adjusted_rand([0, 0, 1, 1], [0, 0, 1, 1]) == 1.0
    assert adjusted_rand([0, 0, 1, 1], [1, 1, 0, 0]) == 1.0  # label-invariant
