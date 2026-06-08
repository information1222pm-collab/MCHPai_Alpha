"""behavior_lab — distribution of Wallet DNA traits across the population."""

from __future__ import annotations

from collections import Counter

from wis.app.observatory import Observatory
from wis.domain.wallet.dna import Trait


def trait_frequencies(obs: Observatory) -> dict[str, int]:
    """How common each DNA trait is across all profiled wallets."""
    counter: Counter[str] = Counter()
    for address in obs.list_wallets():
        frame = obs.wallet_frame(address)
        if frame is None:
            continue
        for trait in (*frame.dna.strengths, *frame.dna.weaknesses, *frame.dna.tendencies):
            counter[trait.value] += 1
    return dict(counter)


def strength_cooccurrence(obs: Observatory, a: Trait, b: Trait) -> int:
    """How many wallets exhibit both strengths ``a`` and ``b`` — the seed of
    archetype discovery."""
    n = 0
    for address in obs.list_wallets():
        frame = obs.wallet_frame(address)
        if frame is None:
            continue
        s = set(frame.dna.strengths)
        if a in s and b in s:
            n += 1
    return n
