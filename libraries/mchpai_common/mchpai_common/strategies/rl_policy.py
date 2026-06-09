"""Self-correcting online RL policy for trade entries (contextual bandit).

The trading decision is framed as a contextual bandit:

    context x  = features at the decision moment (ratio, momentum, smart money,
                 liquidity, buyers, age, imbalance, ...)
    action a   = SKIP (0) or BUY (1)
    reward r   = SKIP -> 0 (the safe baseline)
                 BUY  -> the *realized* return of the trade after realistic costs,
                         delivered when the position closes (delayed reward)

The policy is an online linear model per action trained by SGD, so it:
  * **self-improves** — every closed trade updates the weights toward what
    actually paid,
  * **self-corrects** — exploration (epsilon) rises when recent rewards turn
    negative and relaxes when they're positive, so it adapts to regime change
    instead of stubbornly repeating losing bets,
  * needs no matrix inversion (cheap enough to run live in a browser).

It learns to BUY only in contexts whose expected realized reward beats 0 (skip).
Pure numpy, deterministic given a seed — unit-tested.
"""

from __future__ import annotations

from collections import deque

import numpy as np


class OnlineBandit:
    def __init__(self, dim: int, n_actions: int = 2, *, lr: float = 0.05,
                 eps: float = 0.15, eps_min: float = 0.02, eps_max: float = 0.45,
                 l2: float = 1e-3, seed: int = 0) -> None:
        self.k = n_actions
        self.dim = dim
        self.w = np.zeros((n_actions, dim))
        self.lr = lr
        self.eps = eps
        self.eps_min, self.eps_max = eps_min, eps_max
        self.l2 = l2
        self.rng = np.random.default_rng(seed)
        self.recent: deque[float] = deque(maxlen=60)
        self.updates = 0
        # online feature standardization (Welford)
        self._mean = np.zeros(dim)
        self._M2 = np.ones(dim)
        self._n = 0

    def _observe(self, x: np.ndarray) -> None:
        self._n += 1
        d = x - self._mean
        self._mean += d / self._n
        self._M2 += d * (x - self._mean)

    def _std(self, x: np.ndarray) -> np.ndarray:
        var = self._M2 / max(self._n, 1)
        return (x - self._mean) / np.sqrt(var + 1e-6)

    def q(self, x: np.ndarray) -> np.ndarray:
        xs = self._std(np.asarray(x, dtype=float))
        return self.w @ xs

    def select(self, x: np.ndarray, *, learn_features: bool = True) -> int:
        x = np.asarray(x, dtype=float)
        if learn_features:
            self._observe(x)
        if self.rng.random() < self.eps:
            return int(self.rng.integers(self.k))
        return int(np.argmax(self.q(x)))

    def update(self, action: int, x: np.ndarray, reward: float) -> None:
        xs = self._std(np.asarray(x, dtype=float))
        pred = float(self.w[action] @ xs)
        # online ridge SGD toward the realized reward
        self.w[action] += self.lr * ((reward - pred) * xs - self.l2 * self.w[action])
        self.recent.append(reward)
        self.updates += 1
        m = float(np.mean(self.recent)) if self.recent else 0.0
        # self-correction: explore more when losing, exploit when winning
        self.eps = float(np.clip(self.eps * (1.06 if m < 0 else 0.96), self.eps_min, self.eps_max))

    def recent_reward(self) -> float:
        return float(np.mean(self.recent)) if self.recent else 0.0
