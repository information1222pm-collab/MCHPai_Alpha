"""Realistic execution model — what actually happens when you trade memecoins.

A naive backtest fills at the price you *saw*. Reality is brutal:

  * **Latency** — you detect, decide, sign, and your tx lands ~1-2 slots later.
    By then the price has moved (usually against you on a momentum entry). When a
    forward tick path is available we fill at the *actual* later price; otherwise
    we apply a modeled adverse drift.
  * **Slippage / price impact** — your own order moves the price; impact grows
    with order size relative to (thin) liquidity.
  * **Fees** — pump.fun 1% per side + priority fee + Jito tip + ATA rent.
  * **Failure** — a meaningful fraction of snipe txs fail (slippage cap exceeded,
    or you're simply beaten to it) → the entry is missed, or the exit retries
    worse.
  * **Exit gap risk** — when you're stopping out into a dump, the book is thin and
    you fill materially below your trigger.

This module is pure and deterministic given a seed, so it is unit-testable and
the same costs apply in backtest, paper, and (conceptually) live.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class CostModel:
    detect_latency_ms: int = 350      # observe -> decision
    submit_latency_ms: int = 900      # sign -> landed (~1-2 slots)
    base_slippage_bps: float = 80     # baseline slippage each side
    impact_k: float = 0.9             # price-impact coefficient
    liq_floor_sol: float = 5.0        # liquidity proxy floor
    fee_bps: float = 100              # 1% pump.fun fee per side
    fixed_cost_sol: float = 0.0018    # priority + tip + rent per trade
    fail_prob: float = 0.12           # tx fails / front-run
    exit_gap_bps: float = 150         # extra slippage when exiting into weakness

    def latency_s(self) -> float:
        return (self.detect_latency_ms + self.submit_latency_ms) / 1000.0

    def impact_bps(self, size_sol: float, liq_sol: float) -> float:
        return self.impact_k * (size_sol / max(liq_sol, self.liq_floor_sol)) * 10_000.0


def price_after_latency(tick_path, decision_ts, latency_s, fallback):
    """Price at the first tick >= decision_ts + latency (the price you actually
    get), else an adverse-drifted fallback when the path runs out."""
    target = decision_ts + latency_s
    for ts, price in tick_path:
        if ts >= target and price > 0:
            return price
    return fallback


@dataclass
class Fill:
    ok: bool
    price: float = 0.0
    tokens: float = 0.0
    cost_sol: float = 0.0      # all-in SOL spent (entry) / received (exit)
    slippage_bps: float = 0.0
    fee_sol: float = 0.0
    reason: str = ""


class ExecutionModel:
    def __init__(self, cost: CostModel | None = None, seed: int = 0) -> None:
        self.c = cost or CostModel()
        self.rng = random.Random(seed)

    def buy(self, size_sol, intended_price, liq_sol, *, tick_path=None, decision_ts=0.0) -> Fill:
        if self.rng.random() < self.c.fail_prob:
            return Fill(ok=False, reason="entry_failed")  # beaten / slippage cap
        landed = (price_after_latency(tick_path, decision_ts, self.c.latency_s(), intended_price)
                  if tick_path else intended_price * 1.01)  # +1% adverse drift fallback
        slip = self.c.base_slippage_bps + self.c.impact_bps(size_sol, liq_sol)
        fill = landed * (1 + slip / 10_000.0)               # you buy higher
        fee = size_sol * self.c.fee_bps / 10_000.0 + self.c.fixed_cost_sol
        spend = size_sol
        tokens = max(0.0, (spend - fee)) / fill if fill > 0 else 0.0
        return Fill(ok=True, price=fill, tokens=tokens, cost_sol=spend,
                    slippage_bps=slip, fee_sol=fee, reason="filled")

    def sell(self, tokens, intended_price, liq_sol, *, tick_path=None, decision_ts=0.0, adverse=False) -> Fill:
        # exits rarely fail outright, but they retry a tick later (worse)
        landed = (price_after_latency(tick_path, decision_ts, self.c.latency_s(), intended_price)
                  if tick_path else intended_price * 0.99)
        notional = tokens * landed
        slip = self.c.base_slippage_bps + self.c.impact_bps(notional, liq_sol)
        if adverse:
            slip += self.c.exit_gap_bps
        fill = landed * (1 - slip / 10_000.0)               # you sell lower
        gross = tokens * fill
        fee = gross * self.c.fee_bps / 10_000.0 + self.c.fixed_cost_sol
        proceeds = max(0.0, gross - fee)
        return Fill(ok=True, price=fill, tokens=tokens, cost_sol=proceeds,
                    slippage_bps=slip, fee_sol=fee, reason="filled")
