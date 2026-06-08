"""Unsupervised segmentation instruments — exploratory, not predictive.

These are permitted now not because they are clever, but because *reality asked
for them*: the variance in P(BUG-001) is the signature of a mixture, and finding
the mixture's components is an unsupervised problem. PCA for structure, Gaussian
mixtures / hierarchical / HDBSCAN for the partition, silhouette and BIC to judge
whether structure is real or imagined.

Nothing here predicts, scores, or trades. It draws boundaries reality suggests,
and reports — honestly — how confident those boundaries are. ``scikit-learn`` is
imported lazily (research extra).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from wis.research.segmentation_lab.features import FeatureTable


def _np():
    import numpy as np  # lazy

    return np


def standardize(rows: Sequence[Sequence[float]]):
    """Z-score each feature so no single scale dominates the geometry."""
    np = _np()
    x = np.asarray(rows, dtype=float)
    mu = x.mean(axis=0)
    sd = x.std(axis=0)
    sd[sd == 0] = 1.0
    return (x - mu) / sd


def pca(x, n_components: int = 2):
    from sklearn.decomposition import PCA  # lazy

    model = PCA(n_components=n_components, random_state=0)
    coords = model.fit_transform(x)
    return coords, model.explained_variance_ratio_.tolist()


@dataclass(frozen=True, slots=True)
class GMMSelection:
    best_k: int
    bic_by_k: dict[int, float]
    labels: list[int]


def select_gmm(x, k_range: Sequence[int] = (1, 2, 3, 4, 5, 6)) -> GMMSelection:
    """Fit Gaussian mixtures across k and select by BIC (lower = better). If the
    best model is k=1, reality is telling us there is *no* sub-structure."""
    from sklearn.mixture import GaussianMixture  # lazy

    bic: dict[int, float] = {}
    models = {}
    for k in k_range:
        gm = GaussianMixture(n_components=k, covariance_type="full", random_state=0, n_init=3)
        gm.fit(x)
        bic[k] = float(gm.bic(x))
        models[k] = gm
    best_k = min(bic, key=bic.get)
    labels = models[best_k].predict(x).tolist()
    return GMMSelection(best_k=best_k, bic_by_k=bic, labels=labels)


def hierarchical(x, k: int) -> list[int]:
    from sklearn.cluster import AgglomerativeClustering  # lazy

    return AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(x).tolist()


def hdbscan(x, min_cluster_size: int = 10) -> list[int]:
    from sklearn.cluster import HDBSCAN  # lazy

    return HDBSCAN(min_cluster_size=min_cluster_size).fit_predict(x).tolist()


def silhouette(x, labels: Sequence[int]) -> float | None:
    """Mean silhouette (−1..1). ``None`` if fewer than 2 clusters — you cannot
    score a partition that does not partition."""
    from sklearn.metrics import silhouette_score  # lazy

    uniq = {label for label in labels if label >= 0}
    if len(uniq) < 2:
        return None
    return float(silhouette_score(x, labels))


@dataclass(frozen=True, slots=True)
class ClusterProfile:
    label: int
    size: int
    mean_features: dict[str, float]
    mean_n_swaps: float


def profile(table: FeatureTable, labels: Sequence[int]) -> list[ClusterProfile]:
    """Mean feature values per cluster — how to *read* what a cluster is."""
    np = _np()
    x = np.asarray(table.rows, dtype=float)
    swaps = np.asarray(table.n_swaps, dtype=float)
    out: list[ClusterProfile] = []
    for label in sorted(set(labels)):
        mask = np.asarray(labels) == label
        out.append(
            ClusterProfile(
                label=label,
                size=int(mask.sum()),
                mean_features={k: float(x[mask, i].mean()) for i, k in enumerate(table.feature_keys)},
                mean_n_swaps=float(swaps[mask].mean()) if mask.any() else 0.0,
            )
        )
    return out
