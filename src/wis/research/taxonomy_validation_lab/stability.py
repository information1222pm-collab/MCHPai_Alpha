"""Stability instruments — measure whether structure reproduces.

Three honest questions about a candidate population:

1. **Does a defining axis split?** :func:`bimodality` asks whether a single
   feature (e.g. token-to-token share) is genuinely two-moded — a 1-D existence
   test that is independent of any clustering algorithm.
2. **Does a partition survive resampling?** :func:`consensus_matrix` /
   :func:`cluster_stabilities` measure how often wallet pairs co-cluster across
   bootstraps — stable clusters recur; artifacts dissolve.
3. **Does it reproduce on a fresh sample?** Run the same test on an independent
   universe and compare (driven by :mod:`validate`).

Pure-ish: ``numpy`` / ``scikit-learn`` are imported lazily (research extra).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


def _np():
    import numpy as np

    return np


@dataclass(frozen=True, slots=True)
class Modality:
    n: int
    best_k: int            # 1 or 2 by BIC on the 1-D feature
    bic_1: float
    bic_2: float
    mode_means: tuple[float, ...]
    separation: float      # |m2 - m1| in feature units (0 if unimodal)

    @property
    def is_bimodal(self) -> bool:
        # Two modes are "real" only if BIC prefers k=2 *and* the modes are
        # well separated (gradients with one mode do not count).
        return self.best_k == 2 and self.separation >= 0.3


def bimodality(values: Sequence[float]) -> Modality:
    """1-D existence test: fit 1- vs 2-component Gaussian mixtures, compare BIC."""
    from sklearn.mixture import GaussianMixture

    np = _np()
    x = np.asarray(values, dtype=float).reshape(-1, 1)
    n = len(x)
    if n < 10:
        mean = float(x.mean()) if n > 0 else 0.0
        return Modality(n, 1, float("nan"), float("nan"), (mean,), 0.0)
    g1 = GaussianMixture(1, random_state=0).fit(x)
    g2 = GaussianMixture(2, random_state=0, n_init=3).fit(x)
    bic1, bic2 = float(g1.bic(x)), float(g2.bic(x))
    if bic2 < bic1:
        means = sorted(float(m) for m in g2.means_.ravel())
        return Modality(n, 2, bic1, bic2, tuple(means), abs(means[1] - means[0]))
    return Modality(n, 1, bic1, bic2, (float(g1.means_.ravel()[0]),), 0.0)


def _cluster(x, k: int):
    from sklearn.mixture import GaussianMixture

    return GaussianMixture(k, covariance_type="full", random_state=0, n_init=2).fit_predict(x)


def consensus_matrix(x, k: int, *, n_boot: int = 100, frac: float = 0.8, seed: int = 0):
    """Co-association matrix: P(pair i,j in same cluster | both sampled), over
    ``n_boot`` subsample-and-cluster rounds. The heart of stability."""
    np = _np()
    x = np.asarray(x, dtype=float)
    n = len(x)
    co = np.zeros((n, n))
    cnt = np.zeros((n, n))
    rng = np.random.default_rng(seed)
    m = max(2, int(frac * n))
    for _ in range(n_boot):
        idx = rng.choice(n, size=m, replace=False)
        labels = _cluster(x[idx], k)
        same = labels[:, None] == labels[None, :]
        ii = np.ix_(idx, idx)
        co[ii] += same
        cnt[ii] += 1
    with np.errstate(invalid="ignore", divide="ignore"):
        stability = np.where(cnt > 0, co / cnt, 0.0)
    np.fill_diagonal(stability, 1.0)
    return stability


def cluster_stabilities(consensus, reference_labels: Sequence[int]) -> dict[int, float]:
    """Per-cluster mean within-cluster co-association (0..1). High = the cluster's
    members keep landing together across resamples → it reproduces."""
    np = _np()
    labels = np.asarray(reference_labels)
    out: dict[int, float] = {}
    for c in sorted({int(x) for x in labels}):
        members = np.where(labels == c)[0]
        if len(members) < 2:
            out[c] = float("nan")
            continue
        sub = consensus[np.ix_(members, members)]
        # mean of off-diagonal entries
        n = len(members)
        out[c] = float((sub.sum() - n) / (n * (n - 1)))
    return out


def adjusted_rand(a: Sequence[int], b: Sequence[int]) -> float:
    from sklearn.metrics import adjusted_rand_score

    return float(adjusted_rand_score(a, b))
