"""The default feature catalog — generated, not written.

This module *declares rules* and expands them into hundreds of FeatureSpecs. The
same handful of lines would expand to thousands as base metrics, windows, and
transforms grow — that is the whole point of the Factory. Everything here is
introspectable: each generated spec carries a description and tags.
"""

from __future__ import annotations

from .spec import FeatureSpec, Normalization

# Raw per-snapshot inputs the catalog builds on (match TokenSnapshot fields).
BASE_METRICS = [
    "price_sol", "volume_sol", "liquidity_sol", "market_cap_sol",
    "buyers", "sellers", "unique_traders", "holders", "txns",
    "net_flow_sol", "entropy", "smart_money_ratio", "cluster_ratio",
]

# Rolling windows in history *steps*.
WINDOWS = [3, 5, 10, 20]

# (transform, normalization) applied per base metric per window.
ROLLING = [
    ("rolling_mean", Normalization.none),
    ("rolling_std", Normalization.none),
    ("rolling_max", Normalization.none),
    ("zscore", Normalization.tanh),
    ("rate_of_change", Normalization.tanh),
    ("slope", Normalization.tanh),
    ("acceleration", Normalization.tanh),
    ("ewma", Normalization.none),
]


def build_default_catalog() -> list[FeatureSpec]:
    specs: list[FeatureSpec] = []

    # 1) passthrough of every base metric
    for m in BASE_METRICS:
        specs.append(FeatureSpec(
            name=f"raw.{m}", transform="input", dependencies=(m,),
            description=f"raw value of {m}", tags=("raw",),
        ))

    # 2) rolling/windowed transforms (the bulk — generated combinatorially)
    for m in BASE_METRICS:
        for w in WINDOWS:
            for tname, norm in ROLLING:
                params = (("halflife", float(w)),) if tname == "ewma" else ()
                specs.append(FeatureSpec(
                    name=f"{m}.{tname}.w{w}",
                    transform=tname,
                    dependencies=(m,),
                    window=w,
                    params=params,
                    normalization=norm,
                    description=f"{tname} of {m} over {w} steps",
                    tags=("rolling", m, tname),
                ))

    # 3) hand-picked cross-metric ratios / interactions (still declarative)
    specs += [
        FeatureSpec(name="ratio.buy_sell", transform="ratio",
                    dependencies=("buyers", "sellers"), normalization=Normalization.log1p,
                    description="buyers / sellers", tags=("interaction",)),
        FeatureSpec(name="flow.imbalance", transform="imbalance",
                    dependencies=("buyers", "sellers"),
                    description="order-flow imbalance [-1,1]", tags=("interaction",)),
        FeatureSpec(name="ratio.vol_per_trader", transform="ratio",
                    dependencies=("volume_sol", "unique_traders"),
                    normalization=Normalization.log1p,
                    description="volume per unique trader", tags=("interaction",)),
        FeatureSpec(name="ratio.netflow_to_vol", transform="ratio",
                    dependencies=("net_flow_sol", "volume_sol"),
                    description="net flow as a fraction of volume", tags=("interaction",)),
        FeatureSpec(name="epi.r0_buyers.w10", transform="r0", dependencies=("buyers",),
                    window=10, description="epidemiological R0 of new buyers",
                    tags=("intelligence",)),
        # a derived-of-derived: momentum = roc of the ewma of price
        FeatureSpec(name="price.momentum", transform="diff",
                    dependencies=("price_sol.rolling_mean.w3", "price_sol.rolling_mean.w20"),
                    normalization=Normalization.tanh,
                    description="short minus long price mean (momentum)",
                    tags=("interaction", "momentum")),
    ]
    return specs
