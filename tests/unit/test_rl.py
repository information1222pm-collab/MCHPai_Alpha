"""Tests for the LinUCB contextual-bandit agent — proves it actually learns."""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from models.reinforcement_learning import LinUCBAgent  # noqa: E402


def test_agent_learns_context_dependent_optimal_action():
    """In a world where the best action depends on context, the agent should
    converge to positive reward — i.e. it self-improves from experience."""
    rng = np.random.default_rng(0)
    agent = LinUCBAgent(2, 3, alpha=0.6, epsilon=0.05, seed=1)  # 2 features + bias

    def reward(ctx, action):
        # action 0 is good when feature0=1; action 1 is good when feature1=1
        good = 0 if ctx[0] > ctx[1] else 1
        return 1.0 if action == good else -1.0

    total = 0.0
    last_200 = []
    for t in range(1000):
        f = [1.0, 0.0] if rng.random() < 0.5 else [0.0, 1.0]
        x = np.array(f + [1.0])  # bias term
        a = agent.select(x)
        r = reward(f, a)
        agent.update(a, x, r)
        total += r
        if t >= 800:
            last_200.append(r)

    # after learning, late-stage reward should be strongly positive (mostly correct)
    assert np.mean(last_200) > 0.6
    assert total > 0


def test_agent_beats_random_policy():
    rng = np.random.default_rng(2)
    agent = LinUCBAgent(2, 3, seed=3)

    def reward(ctx, action):
        return 1.0 if action == (0 if ctx[0] > ctx[1] else 1) else -1.0

    agent_total = rand_total = 0.0
    for _ in range(800):
        f = [1.0, 0.0] if rng.random() < 0.5 else [0.0, 1.0]
        x = np.array(f + [1.0])
        a = agent.select(x)
        agent.update(a, x, reward(f, a))
        agent_total += reward(f, a)
        rand_total += reward(f, int(rng.integers(2)))

    assert agent_total > rand_total


def test_self_correction_increases_exploration_when_losing():
    agent = LinUCBAgent(2, 2, alpha=1.0, seed=0)
    base_alpha = agent.alpha
    x = np.array([1.0, 1.0])
    for _ in range(30):
        agent.update(0, x, -1.0)  # a losing streak
    # adaptive exploration should have raised alpha above its base
    assert agent.alpha > base_alpha
    assert agent.recent_reward() < 0
