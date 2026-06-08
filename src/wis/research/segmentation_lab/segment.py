"""Run the segmentation analysis over captured raw sessions.

Loads on-disk raw transactions (no network, no new observation), groups by
wallet, builds the behavioral feature table, and asks the unsupervised
instruments whether latent populations exist. Writes a findings report and a PCA
projection plot. Honest by construction: if BIC prefers k=1 or the silhouette is
near zero, it says so.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path

from wis.research.segmentation_lab import cluster
from wis.research.segmentation_lab.features import build_feature_table, group_by_fee_payer


def _load(paths: Iterable[str | Path]) -> list[dict]:
    txs: list[dict] = []
    for p in paths:
        with open(p) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    txs.append(json.loads(line))
    return txs


def run(
    raw_paths: Mapping[str, str | Path],
    out_dir: str | Path,
    *,
    min_txs: int = 15,
) -> dict:
    """``raw_paths`` maps a universe label -> a raw JSONL path. Returns a report
    dict and writes ``findings.md`` + ``segmentation_pca.png`` under ``out_dir``."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Universe membership (for validation colouring), and the pooled tx set.
    universe_of: dict[str, str] = {}
    all_txs: list[dict] = []
    for label, path in raw_paths.items():
        txs = _load([path])
        all_txs.extend(txs)
        for w in group_by_fee_payer(txs):
            universe_of.setdefault(w, label)

    table = build_feature_table(group_by_fee_payer(all_txs), min_txs=min_txs)
    n = len(table.wallets)
    report: dict = {"n_wallets": n, "min_txs": min_txs, "feature_keys": list(table.feature_keys)}
    if n < 10:
        report["verdict"] = "insufficient wallets for segmentation"
        (out / "findings.md").write_text(_render(report, table, None, None, None, universe_of))
        return report

    x = cluster.standardize(table.rows)
    coords, evr = cluster.pca(x, n_components=2)
    gmm = cluster.select_gmm(x)
    sil = cluster.silhouette(x, gmm.labels)
    profiles = cluster.profile(table, gmm.labels)

    report.update({
        "pca_explained_variance": evr,
        "gmm_best_k": gmm.best_k,
        "gmm_bic_by_k": gmm.bic_by_k,
        "silhouette": sil,
        "clusters": [
            {"label": p.label, "size": p.size, "mean_n_swaps": p.mean_n_swaps, "mean_features": p.mean_features}
            for p in profiles
        ],
    })

    _plot(out / "segmentation_pca.png", coords, gmm.labels, [universe_of.get(w, "?") for w in table.wallets])
    (out / "findings.md").write_text(_render(report, table, coords, gmm, profiles, universe_of))
    return report


def _plot(path: Path, coords, labels, universes) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))
    ax1.scatter(coords[:, 0], coords[:, 1], c=labels, cmap="tab10", s=18, alpha=0.8)
    ax1.set_title("Wallets in behavioral PCA space — coloured by GMM cluster")
    ax1.set_xlabel("PC1")
    ax1.set_ylabel("PC2")

    uniq = sorted(set(universes))
    idx = {u: i for i, u in enumerate(uniq)}
    ax2.scatter(coords[:, 0], coords[:, 1], c=[idx[u] for u in universes], cmap="Set2", s=18, alpha=0.8)
    ax2.set_title("Same space — coloured by discovery universe")
    ax2.set_xlabel("PC1")
    ax2.set_ylabel("PC2")
    handles = [plt.Line2D([0], [0], marker="o", ls="", color=plt.cm.Set2(idx[u] / max(len(uniq) - 1, 1)), label=u) for u in uniq]
    ax2.legend(handles=handles, fontsize=8, loc="best")

    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def _render(report, table, coords, gmm, profiles, universe_of) -> str:
    lines = ["# Segmentation findings\n",
             "Exploratory unsupervised analysis over **captured raw sessions** (no new",
             "observation). Wallets grouped by fee payer; only wallets with "
             f"≥ {report['min_txs']} transactions are included (small denominators lie).\n",
             f"* **Wallets analysed**: {report['n_wallets']}"]
    if report.get("verdict"):
        lines.append(f"\n**Verdict:** {report['verdict']}.")
        return "\n".join(lines)

    evr = report["pca_explained_variance"]
    lines.append(f"* **PCA (2D) explained variance**: PC1 {evr[0]:.0%}, PC2 {evr[1]:.0%}")
    bic = report["gmm_bic_by_k"]
    lines.append("* **Gaussian mixture model selection (BIC, lower=better)**: "
                 + ", ".join(f"k={k}:{v:.0f}" for k, v in bic.items()))
    sil = report["silhouette"]
    lines.append(f"* **Best k by BIC**: **{report['gmm_best_k']}** · silhouette "
                 f"{sil:.3f}" if sil is not None else f"* **Best k by BIC**: {report['gmm_best_k']} · silhouette n/a")
    lines.append("")

    if report["gmm_best_k"] == 1:
        lines.append("**Verdict: no latent sub-structure detected.** BIC prefers a single "
                     "Gaussian — at this sample size and feature set, 'active traders' does not "
                     "split. The variance may be continuous, not clustered. We do not invent classes.")
    else:
        lines.append(f"**Verdict: {report['gmm_best_k']} candidate populations.** The label "
                     "decomposes. Cluster profiles below — read `frac_token_to_token` to see how "
                     "the BUG-001 mixture is partitioned.\n")
        lines.append("| cluster | size | mean swaps | frac_t2t | frac_sol_paired | jupiter | frac_swap | mechanics |")
        lines.append("|--------:|-----:|-----------:|---------:|----------------:|--------:|----------:|----------:|")
        for p in profiles:
            mf = p.mean_features
            lines.append(f"| {p.label} | {p.size} | {p.mean_n_swaps:.0f} | "
                         f"{mf['frac_token_to_token']:.2f} | {mf['frac_sol_paired']:.2f} | "
                         f"{mf['jupiter_share']:.2f} | {mf['frac_swap']:.2f} | {mf['mechanics_ratio']:.2f} |")

    lines.append("\n*Caveat:* exploratory. Cluster counts depend on the feature set and sample; "
                 "silhouette near 0 means weakly separated. See `segmentation_pca.png`. This is a "
                 "hypothesis about reality's categories, to be confirmed by replication — not a fact.")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="wis.research.segmentation_lab.segment")
    parser.add_argument("--out-dir", default="sessions/segmentation")
    parser.add_argument("--min-txs", type=int, default=15)
    parser.add_argument("--raw", action="append", default=[], metavar="LABEL=PATH",
                        help="universe label and raw JSONL path, repeatable")
    args = parser.parse_args()
    raw = dict(item.split("=", 1) for item in args.raw)
    rep = run(raw, args.out_dir, min_txs=args.min_txs)
    print(json.dumps({k: v for k, v in rep.items() if k != "clusters"}, indent=2))
