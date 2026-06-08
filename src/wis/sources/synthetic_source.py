"""SyntheticSource — a deterministic reality generator for chaos testing.

Reality is messy: oversells, dust, zero-value transfers, out-of-order
timestamps, duplicates. A robust observatory must ingest all of it without
crashing and without losing determinism. This source manufactures that mess on
purpose — seeded, so the same configuration always produces the same stream,
which makes adversarial and fault-injection tests reproducible.

It emits only *valid* domain events (the door is the same for everyone); the
adversarial part is the *content* — the kind of event the world will eventually
throw at us. The seeded RNG is the only source of variation: no wall clock, no
global state, so the stream is a pure function of the config.
"""

from __future__ import annotations

import random
from collections.abc import Iterator
from dataclasses import dataclass

from wis.domain.time import DAY, Nanos
from wis.sources import build
from wis.sources.base import SourcedEvent

TOKEN_DECIMALS = 6
QUOTE_DECIMALS = 9


@dataclass(frozen=True, slots=True)
class SyntheticConfig:
    seed: int = 0
    n_wallets: int = 5
    n_tokens: int = 8
    n_events: int = 200
    fault_rate: float = 0.0  # probability a given event is adversarial
    start_time: int = DAY


class SyntheticSource:
    def __init__(self, config: SyntheticConfig | None = None, *, name: str = "synthetic") -> None:
        self.config = config or SyntheticConfig()
        self.name = name

    def event_stream(self) -> Iterator[SourcedEvent]:
        cfg = self.config
        rng = random.Random(cfg.seed)  # re-seeded each call → repeatable stream
        wallets = [f"w{i}" for i in range(cfg.n_wallets)]
        tokens = [f"t{i}" for i in range(cfg.n_tokens)]
        # holdings[(wallet, token)] = base units currently held (raw int)
        holdings: dict[tuple[str, str], int] = {}
        t = cfg.start_time

        # Birth every wallet first.
        for w in wallets:
            t += rng.randint(1, 5) * 1_000_000_000
            yield SourcedEvent(payload=build.created(w, t), ingestion_time=Nanos(t))

        for _ in range(cfg.n_events):
            t += rng.randint(1, 3600) * 1_000_000_000
            wallet = rng.choice(wallets)
            token = rng.choice(tokens)
            fault = rng.random() < cfg.fault_rate

            held = holdings.get((wallet, token), 0)
            # Decide action: buy if nothing held, else sometimes sell.
            do_sell = held > 0 and rng.random() < 0.5

            if do_sell:
                if fault:
                    # Oversell: dispose of more than is held.
                    base_raw = held + rng.randint(1, 1000) * 10**TOKEN_DECIMALS
                else:
                    base_raw = rng.randint(1, max(1, held // (10**TOKEN_DECIMALS))) * 10**TOKEN_DECIMALS
                    base_raw = min(base_raw, held)
                quote_raw = rng.randint(1, 50) * 10 ** (QUOTE_DECIMALS - 2)
                occurred = self._maybe_backwards(rng, t, fault)
                yield SourcedEvent(
                    payload=build.sell(
                        wallet,
                        token,
                        build.amount_from_raw(base_raw, TOKEN_DECIMALS),
                        build.amount_from_raw(quote_raw, QUOTE_DECIMALS),
                        occurred,
                    ),
                    ingestion_time=Nanos(t),
                )
                holdings[(wallet, token)] = max(0, held - base_raw)
            else:
                if fault and rng.random() < 0.5:
                    base_raw = 0  # zero / dust buy — ledger must shrug it off
                else:
                    base_raw = rng.randint(1, 5000) * 10**TOKEN_DECIMALS
                quote_raw = rng.randint(1, 100) * 10 ** (QUOTE_DECIMALS - 2)
                occurred = self._maybe_backwards(rng, t, fault)
                yield SourcedEvent(
                    payload=build.buy(
                        wallet,
                        token,
                        build.amount_from_raw(base_raw, TOKEN_DECIMALS),
                        build.amount_from_raw(quote_raw, QUOTE_DECIMALS),
                        occurred,
                    ),
                    ingestion_time=Nanos(t),
                )
                holdings[(wallet, token)] = held + base_raw

    @staticmethod
    def _maybe_backwards(rng: random.Random, t: int, fault: bool) -> int:
        """Occasionally emit an event whose world-time precedes its ingestion —
        an out-of-order observation the system must tolerate."""
        if fault and rng.random() < 0.3:
            return max(0, t - rng.randint(1, 48) * 3600 * 1_000_000_000)
        return t
