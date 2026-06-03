"""Ecology — the market as an ecosystem of interacting species of wallets.

Snipers, insiders, market-makers, bots, and retail occupy different *niches* and
relate as predator/prey. Ecological models give us carrying capacity (how much a
token can absorb), competition pressure, and Lotka-Volterra dynamics between
"predator" (early smart money) and "prey" (late retail) populations.

    * Predators arriving before prey  -> early; healthy food chain (bullish).
    * Prey peaking with predators exiting -> top; distribution (bearish).
"""

from __future__ import annotations

import numpy as np


def shannon_diversity(population_by_species: dict[str, int]) -> float:
    """Shannon diversity index of the wallet population (higher = healthier)."""
    counts = np.array([c for c in population_by_species.values() if c > 0], dtype=float)
    if counts.size == 0:
        return 0.0
    p = counts / counts.sum()
    return float(-np.sum(p * np.log(p)))


def carrying_capacity(liquidity_sol: float, holders: int, k: float = 1.0) -> float:
    """Estimated capacity (max absorbable inflow) before saturation."""
    return float(k * liquidity_sol * np.log1p(max(holders, 0)))


def logistic_growth(population: float, capacity: float, rate: float) -> float:
    """One logistic step: growth slows as population nears carrying capacity."""
    if capacity <= 0:
        return population
    return population + rate * population * (1.0 - population / capacity)


def predator_prey_phase(predators: float, prey: float) -> str:
    """Classify the food-chain phase from predator/prey populations."""
    if prey <= 0:
        return "barren"
    ratio = predators / prey
    if ratio > 0.5:
        return "predator_dominant"   # smart money heavy, retail thin -> early
    if ratio < 0.1:
        return "prey_dominant"       # retail heavy, smart money exiting -> late
    return "balanced"
