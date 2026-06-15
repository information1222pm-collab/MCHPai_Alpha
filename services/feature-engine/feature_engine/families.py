"""Feature families — composable feature plugins.

Each family is a pure function ``(context) -> dict[str, float]``. Registering a
new family adds features platform-wide. Families lean directly on the first-class
domain sciences (entropy, epidemiology, ecology, astronomy) so the "exotic"
libraries are wired into production features, not just research.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from mchpai_common import astronomy, ecology, entropy, epidemiology, indicators

FeatureFamily = Callable[[dict], dict[str, float]]
_REGISTRY: dict[str, FeatureFamily] = {}


def family(name: str):
    def deco(fn: FeatureFamily) -> FeatureFamily:
        _REGISTRY[name] = fn
        return fn

    return deco


def registry() -> dict[str, FeatureFamily]:
    return dict(_REGISTRY)


# ---- creator features ------------------------------------------------------
@family("creator")
def creator_features(ctx: dict) -> dict[str, float]:
    return {
        "creator_prior_tokens": float(ctx.get("creator_prior_tokens", 0)),
        "creator_rug_rate": float(ctx.get("creator_rug_rate", 0.0)),
        "creator_success_rate": float(ctx.get("creator_success_rate", 0.0)),
    }


# ---- liquidity features ----------------------------------------------------
@family("liquidity")
def liquidity_features(ctx: dict) -> dict[str, float]:
    liq = float(ctx.get("liquidity_sol", 0.0))
    return {
        "liquidity_sol": liq,
        "liquidity_log": float(np.log1p(liq)),
        "lp_burned": 1.0 if ctx.get("lp_burned") else 0.0,
    }


# ---- spread / order-flow features ------------------------------------------
@family("spread")
def spread_features(ctx: dict) -> dict[str, float]:
    buys = float(ctx.get("buys_1m", 0))
    sells = float(ctx.get("sells_1m", 0))
    return {
        "flow_imbalance": indicators.imbalance(buys, sells),
        "buy_sell_ratio": buys / sells if sells > 0 else buys,
        "holder_gini": indicators.gini(np.asarray(ctx.get("holder_balances", []), dtype=float)),
    }


# ---- entropy features (information theory) ----------------------------------
@family("entropy")
def entropy_features(ctx: dict) -> dict[str, float]:
    buyers = ctx.get("buyer_sol_amounts", {})
    return {
        "buyer_entropy": entropy.buyer_entropy(buyers) if buyers else 0.0,
        "distinct_buyers": float(len(buyers)),
    }


# ---- attention features (epidemiology + astronomy) -------------------------
@family("attention")
def attention_features(ctx: dict) -> dict[str, float]:
    new_buyers = np.asarray(ctx.get("new_buyers_series", []), dtype=float)
    r0 = epidemiology.estimate_r0(new_buyers) if new_buyers.size else 0.0
    mass = astronomy.token_mass(
        ctx.get("liquidity_sol", 0.0), int(ctx.get("holders", 0)), ctx.get("volume_1m", 0.0)
    )
    velocity = indicators.rate_of_change(new_buyers) if new_buyers.size else 0.0
    attention = float(mass * (1.0 + max(velocity, 0.0)))
    return {
        "r0": r0,
        "token_mass": mass,
        "attention": attention,
        "attention_velocity": velocity,
        "luminosity": astronomy.luminosity(attention, velocity),
    }


# ---- ecology features ------------------------------------------------------
@family("ecology")
def ecology_features(ctx: dict) -> dict[str, float]:
    pop = ctx.get("population_by_label", {})
    return {
        "wallet_diversity": ecology.shannon_diversity(pop) if pop else 0.0,
        "carrying_capacity": ecology.carrying_capacity(
            ctx.get("liquidity_sol", 0.0), int(ctx.get("holders", 0))
        ),
    }


def compute_all(ctx: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    for name, fn in _REGISTRY.items():
        for k, v in fn(ctx).items():
            out[f"{name}.{k}"] = float(v)
    return out
