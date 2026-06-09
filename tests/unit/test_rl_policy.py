"""Tests for the self-correcting online RL trading policy (contextual bandit)."""

import numpy as np

from mchpai_common.strategies import OnlineBandit


def test_learns_to_buy_good_contexts_and_skip_bad():
    """Context feature 0 = 'quality'. High quality -> BUY pays +1, low -> -1.
    SKIP always pays 0. The policy should learn to BUY good, SKIP bad."""
    rng = np.random.default_rng(0)
    bot = OnlineBandit(dim=2, n_actions=2, eps=0.2, seed=1)  # [quality, bias]

    def reward(quality, action):
        if action == 0:           # skip
            return 0.0
        return 1.0 if quality > 0 else -1.0  # buy

    for _ in range(2000):
        quality = 1.0 if rng.random() < 0.5 else -1.0
        x = np.array([quality, 1.0])
        a = bot.select(x)
        bot.update(a, x, reward(quality, a))

    # after learning: BUY good context, SKIP bad context (greedy)
    good = np.array([1.0, 1.0]); bad = np.array([-1.0, 1.0])
    assert int(np.argmax(bot.q(good))) == 1   # buy the good one
    assert int(np.argmax(bot.q(bad))) == 0    # skip the bad one


def test_self_corrects_exploration_when_losing():
    bot = OnlineBandit(dim=2, eps=0.1, seed=2)
    base = bot.eps
    x = np.array([1.0, 1.0])
    for _ in range(40):
        bot.update(1, x, -1.0)     # a losing streak
    assert bot.eps > base          # exploration rose to escape the losing policy
    assert bot.recent_reward() < 0


def test_exploitation_relaxes_when_winning():
    bot = OnlineBandit(dim=2, eps=0.3, seed=3)
    x = np.array([1.0, 1.0])
    for _ in range(60):
        bot.update(1, x, 1.0)      # winning
    assert bot.eps < 0.3           # exploration shrank to exploit the edge


def test_improves_reward_over_time():
    rng = np.random.default_rng(4)
    bot = OnlineBandit(dim=3, eps=0.2, seed=4)

    def reward(x, a):
        return 0.0 if a == 0 else (1.0 if x[0] + x[1] > 0 else -1.0)

    early, late = [], []
    for i in range(3000):
        x = np.array([rng.normal(), rng.normal(), 1.0])
        a = bot.select(x)
        r = reward(x, a)
        bot.update(a, x, r)
        (early if i < 500 else late).append(r if i < 500 or i >= 2500 else 0)
    assert np.mean([v for v in late if v != 0] or [0]) >= np.mean(early)
