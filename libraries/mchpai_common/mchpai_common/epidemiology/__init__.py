"""Epidemiology — modeling how a token *infects* the wallet population.

A memecoin spreads like a contagion: a few "infected" wallets buy, expose their
graph neighbors, who buy in turn. SIR/SEIR dynamics and the basic reproduction
number R0 give us a principled way to measure virality and forecast the curve.

    R0 > 1  -> spreading (each buyer triggers >1 new buyer): early, bullish.
    R0 < 1  -> burning out: late, distribution phase.

These features feed the prediction-engine and the AttentionSpike signal.
"""

from __future__ import annotations

import numpy as np


def estimate_r0(new_buyers_per_interval: np.ndarray, recovery_intervals: float = 1.0) -> float:
    """Estimate R0 from the growth rate of *new* buyers.

    Uses the exponential-growth approximation R0 ≈ 1 + r·D, where r is the
    per-interval growth rate of new infections and D the infectious period.
    """
    x = np.asarray(new_buyers_per_interval, dtype=float)
    x = x[x > 0]
    if x.size < 2:
        return 0.0
    log_growth = np.diff(np.log(x))
    r = float(np.mean(log_growth))
    return max(0.0, 1.0 + r * recovery_intervals)


def infection_pressure(infected_neighbors: int, susceptible_neighbors: int, beta: float = 0.3) -> float:
    """Per-wallet probability of 'infection' (buying) given its neighborhood."""
    if susceptible_neighbors <= 0:
        return 0.0
    contacts = infected_neighbors
    return float(1.0 - np.exp(-beta * contacts))


def sir_step(s: float, i: float, r: float, beta: float, gamma: float, n: float) -> tuple[float, float, float]:
    """One discrete SIR step. Population N = S+I+R (here: candidate wallets)."""
    new_inf = beta * s * i / n if n > 0 else 0.0
    new_rec = gamma * i
    return s - new_inf, i + new_inf - new_rec, r + new_rec


def simulate_sir(s0: float, i0: float, beta: float, gamma: float, steps: int = 50) -> list[tuple[float, float, float]]:
    """Project the spread curve — used to forecast peak attention/timing."""
    n = s0 + i0
    s, i, r = s0, i0, 0.0
    out = []
    for _ in range(steps):
        s, i, r = sir_step(s, i, r, beta, gamma, n)
        out.append((s, i, r))
    return out
