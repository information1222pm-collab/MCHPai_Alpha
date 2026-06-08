"""YellowstoneSource — high-performance live observation via Geyser/Yellowstone.

Yellowstone streams Solana updates at very low latency over gRPC. The raw stream
is account/transaction bytes; a decoding layer normalizes those into structured
swap/transfer messages. ``YellowstoneSource`` translates that *normalized* shape
into domain events — keeping the valuable logic pure and testable while the gRPC
transport and program decoding stay separable concerns.

Like every source, it emits the same domain events as all the others. Ingestion
time is stamped at receipt; capture into an archive for deterministic replay.
Translation is verified against sample messages, pending a live endpoint.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator

from wis.domain.events import DomainEvent
from wis.domain.time import Nanos, now_nanos
from wis.sources import build
from wis.sources.base import SourcedEvent

_LAMPORT_DECIMALS = 9


def translate_yellowstone(update: dict) -> list[DomainEvent]:
    """Pure: one normalized Yellowstone update → zero or more domain events.

    Expected normalized shape::

        {"block_time": <seconds>, "kind": "swap"|"transfer", ...}

    swap:     wallet, side ("buy"/"sell"), token{mint,amount,decimals}, sol_lamports
    transfer: source, target, lamports
    """
    at = int(update["block_time"]) * 1_000_000_000
    kind = update["kind"]

    if kind == "swap":
        wallet = update["wallet"]
        token = update["token"]
        base = build.amount_from_raw(int(token["amount"]), int(token["decimals"]))
        quote = build.amount_from_raw(int(update["sol_lamports"]), _LAMPORT_DECIMALS)
        if update["side"] == "buy":
            return [build.buy(wallet, token["mint"], base, quote, at, venue="yellowstone")]
        return [build.sell(wallet, token["mint"], base, quote, at, venue="yellowstone")]

    if kind == "transfer":
        amount = build.amount_from_raw(int(update["lamports"]), _LAMPORT_DECIMALS)
        return [build.funding(update["source"], update["target"], amount, at)]

    return []


class YellowstoneSource:
    def __init__(
        self,
        updates: Iterable[dict],
        *,
        now: Callable[[], Nanos] = now_nanos,
        name: str = "yellowstone",
    ) -> None:
        self._updates = updates
        self._now = now
        self.name = name

    def event_stream(self) -> Iterator[SourcedEvent]:
        for update in self._updates:
            ingestion = self._now()
            for payload in translate_yellowstone(update):
                yield SourcedEvent(payload=payload, ingestion_time=ingestion)
