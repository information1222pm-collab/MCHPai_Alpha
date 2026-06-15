"""Astronomy — gravity & attention models for tokens.

We treat each token as a body with *mass* (liquidity + holders + attention). Mass
exerts gravitational pull on capital; a token's trajectory can be modeled like an
orbit. This gives elegant, scale-free features: gravitational attraction between
a wallet's capital and a token, escape velocity (the inflow needed to keep
climbing), and "luminosity" (how brightly a token shines in attention space).
"""

from __future__ import annotations

import numpy as np

G = 1.0  # dimensionless coupling constant (calibrated empirically)


def token_mass(liquidity_sol: float, holders: int, volume_sol: float) -> float:
    """Composite 'mass' of a token in attention-space."""
    return float(liquidity_sol + 0.5 * volume_sol + 10.0 * np.log1p(max(holders, 0)))


def gravitational_pull(capital_sol: float, mass: float, distance: float) -> float:
    """Newtonian pull F = G·m1·m2 / r².

    ``distance`` is a dissimilarity (e.g. how far a token is from a wallet's
    usual niche); closer + heavier = stronger pull to buy.
    """
    r = max(distance, 1e-6)
    return float(G * capital_sol * mass / (r * r))


def escape_velocity(mass: float, radius: float) -> float:
    """Inflow 'velocity' required to avoid falling back (price decay)."""
    r = max(radius, 1e-6)
    return float(np.sqrt(2.0 * G * mass / r))


def luminosity(attention: float, velocity: float) -> float:
    """How brightly a token shines = attention scaled by its rate of change."""
    return float(attention * (1.0 + max(velocity, 0.0)))
