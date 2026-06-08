"""Run taxonomy validation over captured sessions — existence, not identity.

Two tests, both honest and key-free (each universe is an independent sample):

* **Existence (Test A).** Is the defining axis ``frac_token_to_token`` genuinely
  bimodal among swap-active wallets — and does that bimodality reproduce in every
  independent universe? Algorithm-free; the cleanest "does the split exist?".
* **Stability (Test B).** On the pooled wallets, how stable is the candidate
  partition under resampling (consensus co-association per cluster)?

Writes ``validation_findings.md`` + a per-universe modality figure. Clusters stay
anonymous; nothing is named.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from wis.research.segmentation_lab import cluster
from wis.research.segmentation_lab.features import build_feature_table, group_by_fee_payer
from wis.research.taxonomy_validation_lab import stability

_SWAP_ACTIVE_MIN = 5  # a frac_token_to_token over <5 swaps is meaningless


def _load(path: str | Path) -> list[dict]:
    out = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _t2t_column(table) -> list[tuple[float, int]]:
    j = table.feature_keys.index("frac_token_to_token")
    return [(table.rows[i][j], table.n_swaps[i]) for i in range(len(table.wallets))]


def run(raw_paths: Mapping[str, str | Path], out_dir: str | Path) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report: dict = {"existence": {}, "stability": {}}

    # ---- Test A: existence of the t2t split, per independent universe ----
    pooled_txs: list[dict] = []
    universe_t2t: dict[str, list[float]] = {}
    for label, path in raw_paths.items():
        txs = _load(path)
        pooled_txs.extend(txs)
        table = build_feature_table(group_by_fee_payer(txs), min_txs=15)
        vals = [v for v, ns in _t2t_column(table) if ns >= _SWAP_ACTIVE_MIN]
        universe_t2t[label] = vals
        m = stability.bimodality(vals)
        report["existence"][label] = {
            "n_swap_active": m.n, "best_k": m.best_k, "is_bimodal": m.is_bimodal,
            "mode_means": [round(x, 3) for x in m.mode_means], "separation": round(m.separation, 3),
        }

    reproduced = sum(1 for r in report["existence"].values() if r["is_bimodal"])
    report["existence_reproduced_in"] = f"{reproduced}/{len(raw_paths)} universes"

    # ---- Test B: membership stability of the pooled candidate partition ----
    pooled = build_feature_table(group_by_fee_payer(pooled_txs), min_txs=15)
    if len(pooled.wallets) >= 20:
        x = cluster.standardize(pooled.rows)
        gmm = cluster.select_gmm(x)
        consensus = stability.consensus_matrix(x, gmm.best_k, n_boot=120, frac=0.8)
        stabilities = stability.cluster_stabilities(consensus, gmm.labels)
        profiles = cluster.profile(pooled, gmm.labels)
        j = pooled.feature_keys.index("frac_token_to_token")
        report["stability"] = {
            "n_wallets": len(pooled.wallets),
            "best_k": gmm.best_k,
            "clusters": [
                {
                    "cluster": f"Cluster{p.label}",
                    "size": p.size,
                    "stability": round(stabilities.get(p.label, float("nan")), 3),
                    "mean_t2t": round(p.mean_features["frac_token_to_token"], 3),
                    "verdict": _verdict(stabilities.get(p.label, 0.0), p.size),
                }
                for p in profiles
            ],
        }
        _ = j  # (kept for clarity; t2t already in profile)

    _plot_modality(out / "validation_modality.png", universe_t2t)
    (out / "validation_findings.md").write_text(_render(report))
    return report


def _verdict(stab: float, size: int) -> str:
    if size < 8:
        return "too small to judge"
    if stab >= 0.6:
        return "REPRODUCES (stable)"
    if stab >= 0.4:
        return "weak / gradient"
    return "does not reproduce"


def _plot_modality(path: Path, universe_t2t: dict[str, list[float]]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [k for k, v in universe_t2t.items() if len(v) >= 10]
    if not labels:
        return
    cols = 2
    rows = (len(labels) + 1) // 2
    fig, axes = plt.subplots(rows, cols, figsize=(11, 3.2 * rows), squeeze=False)
    for ax in axes.ravel():
        ax.axis("off")
    for i, label in enumerate(labels):
        ax = axes[i // cols][i % cols]
        ax.axis("on")
        ax.hist(universe_t2t[label], bins=20, range=(0, 1), color="#4C72B0", alpha=0.85)
        ax.set_title(f"{label}  (n={len(universe_t2t[label])} swap-active)")
        ax.set_xlabel("frac_token_to_token")
        ax.set_ylabel("wallets")
    fig.suptitle("Existence test: is the token-to-token split bimodal in each independent sample?")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def _render(report: dict) -> str:
    lines = ["# Taxonomy validation — does the candidate split exist?\n",
             "Existence before identity. Clusters stay anonymous. Over captured raw sessions",
             "(no new observation); each universe is an independent sample.\n",
             "## Test A — bimodality of `frac_token_to_token` (algorithm-free)\n",
             "| universe | swap-active n | best k (1-D) | modes | separation | bimodal? |",
             "|----------|--------------:|:-----------:|-------|-----------:|:--------:|"]
    for label, r in report["existence"].items():
        lines.append(f"| {label} | {r['n_swap_active']} | {r['best_k']} | {r['mode_means']} | "
                     f"{r['separation']} | {'YES' if r['is_bimodal'] else 'no'} |")
    lines.append(f"\n**Reproduced in {report['existence_reproduced_in']}.** A split that appears as "
                 "two well-separated modes in independent samples *exists*, independent of any "
                 "clustering choice.\n")

    if report.get("stability"):
        s = report["stability"]
        lines.append(f"## Test B — membership stability (consensus over resampling, pooled n={s['n_wallets']}, k={s['best_k']})\n")
        lines.append("| cluster | size | mean t2t | consensus stability | verdict |")
        lines.append("|---------|-----:|---------:|--------------------:|---------|")
        for c in s["clusters"]:
            lines.append(f"| {c['cluster']} | {c['size']} | {c['mean_t2t']} | {c['stability']} | {c['verdict']} |")
        lines.append("\nStability = mean within-cluster co-association across 120 bootstraps "
                     "(how often members re-cluster together). ≥0.6 reproduces; 0.4–0.6 is a "
                     "gradient; <0.4 is likely an artifact.\n")

    lines.append("## Verdict\n")
    lines.append("Existence is judged by reproduction, not by a single clustering. Anything that "
                 "does not reproduce keeps its anonymous id and earns **no name**. Names are "
                 "privileges granted by stability. See `validation_modality.png`.")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(prog="wis.research.taxonomy_validation_lab.validate")
    p.add_argument("--out-dir", default="sessions/validation")
    p.add_argument("--raw", action="append", default=[], metavar="LABEL=PATH")
    args = p.parse_args()
    raw = dict(item.split("=", 1) for item in args.raw)
    rep = run(raw, args.out_dir)
    print(json.dumps(rep, indent=2))
