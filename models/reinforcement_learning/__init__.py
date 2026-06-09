"""Reinforcement learning — self-improving, self-correcting decision policies.

At MCHPAI's data scale the correct RL formulation is a **contextual bandit**, not
deep RL: each token is one decision (context -> action -> realized reward), which
is sample-efficient and honest. The agent:

  * self-improves  — updates its policy online from every realized reward,
  * self-corrects  — a forgetting factor + adaptive exploration let it adapt to
                     regime change and back off when recent rewards turn negative,
  * stays gated    — it runs in paper/shadow mode and is only eligible for live
                     promotion once it beats the always-buy / always-skip baselines
                     over enough matured episodes.

Full deep RL (PPO/DQN over a market simulator) is deliberately deferred to the
`simulation/` phase, once millions of real episodes exist.
"""

from .bandit import LinUCBAgent

__all__ = ["LinUCBAgent"]
