"""LinUCB contextual bandit — the self-improving / self-correcting core.

Disjoint LinUCB: one linear reward model per action with an upper-confidence
bonus for principled exploration. Online updates make it self-improving; a
forgetting factor (``lam < 1``) plus adaptive exploration make it self-correcting
under non-stationarity (memecoin regimes shift constantly).

Pure numpy — no heavy deps, fully deterministic given a seed, unit-testable.
"""

from __future__ import annotations

import numpy as np


class LinUCBAgent:
    def __init__(
        self,
        n_actions: int,
        dim: int,
        *,
        alpha: float = 1.0,        # exploration strength (UCB width)
        l2: float = 1.0,           # ridge prior
        forgetting: float = 0.999, # <1 ⇒ discount old data (adapt to regime change)
        epsilon: float = 0.03,     # epsilon-greedy floor
        adapt: bool = True,        # self-correct exploration from recent reward
        seed: int = 0,
    ) -> None:
        self.k, self.d = n_actions, dim
        self.alpha0 = self.alpha = alpha
        self.lam = forgetting
        self.eps = epsilon
        self.adapt = adapt
        self.A = [np.eye(dim) * l2 for _ in range(n_actions)]
        self.b = [np.zeros(dim) for _ in range(n_actions)]
        self.rng = np.random.default_rng(seed)
        self._recent: list[float] = []
        self.updates = 0

    def scores(self, x: np.ndarray) -> np.ndarray:
        out = np.empty(self.k)
        for a in range(self.k):
            Ainv = np.linalg.inv(self.A[a])
            theta = Ainv @ self.b[a]
            out[a] = float(theta @ x + self.alpha * np.sqrt(max(x @ Ainv @ x, 1e-9)))
        return out

    def select(self, x: np.ndarray) -> int:
        if self.rng.random() < self.eps:
            return int(self.rng.integers(self.k))
        return int(np.argmax(self.scores(x)))

    def expected(self, x: np.ndarray) -> np.ndarray:
        """Greedy expected reward per action (no exploration bonus)."""
        return np.array([np.linalg.solve(self.A[a], self.b[a]) @ x for a in range(self.k)])

    def update(self, action: int, x: np.ndarray, reward: float) -> None:
        self.A[action] = self.lam * self.A[action] + np.outer(x, x)
        self.b[action] = self.lam * self.b[action] + reward * x
        self.updates += 1
        if self.adapt:
            self._recent.append(reward)
            self._recent = self._recent[-50:]
            m = float(np.mean(self._recent)) if self._recent else 0.0
            # self-correction: losing lately ⇒ explore more; winning ⇒ exploit more
            self.alpha = float(np.clip(self.alpha0 * (1.6 if m < 0 else 0.7), 0.2, 3.0))

    def recent_reward(self) -> float:
        return float(np.mean(self._recent)) if self._recent else 0.0
