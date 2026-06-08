"""HeliusSource — live observation via Helius Enhanced Transactions.

Helius decodes Solana transactions into a friendly JSON shape. The valuable,
testable part is the **translation** of that shape into our domain events; the
network transport that fetches the shape is a thin, separable concern. So
``HeliusSource`` consumes *any* iterable of Helius payload dicts (a captured
file, a webhook queue, a live HTTP poll) and translates each — which means the
translation is fully verifiable in-process with sample payloads, while the live
wiring stays a small lazy adapter.

Ingestion time is stamped at *receipt* (``now``), reflecting when we actually
learned of the event. For deterministic replay, capture the emitted
SourcedEvents into an :class:`~wis.sources.archive_source.ArchiveSource`, which
preserves that ingestion time. Live feeds are reality (non-deterministic timing);
archives are the laboratory.

Translation follows the documented Helius Enhanced Transaction schema; it is
verified against sample payloads and pending verification against a live feed.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator

from wis.domain.events import DomainEvent
from wis.domain.time import Nanos, now_nanos
from wis.sources import build
from wis.sources.base import SourcedEvent

_LAMPORT_DECIMALS = 9


def _amount_field(token_obj: dict):
    raw = token_obj["rawTokenAmount"]
    return build.amount_from_raw(int(raw["tokenAmount"]), int(raw["decimals"]))


def translate_helius(tx: dict) -> list[DomainEvent]:
    """Pure: one Helius enhanced transaction → zero or more domain events."""
    at = int(tx["timestamp"]) * 1_000_000_000  # block time (seconds) → nanos
    wallet = tx.get("feePayer")
    out: list[DomainEvent] = []

    swap = (tx.get("events") or {}).get("swap")
    if swap:
        native_in = swap.get("nativeInput")
        native_out = swap.get("nativeOutput")
        token_in = swap.get("tokenInputs") or []
        token_out = swap.get("tokenOutputs") or []
        if native_in and token_out:  # SOL spent, token received -> BUY
            quote = build.amount_from_raw(int(native_in["amount"]), _LAMPORT_DECIMALS)
            out.append(build.buy(wallet, token_out[0]["mint"], _amount_field(token_out[0]), quote, at, venue="helius"))
        elif token_in and native_out:  # token spent, SOL received -> SELL
            quote = build.amount_from_raw(int(native_out["amount"]), _LAMPORT_DECIMALS)
            out.append(build.sell(wallet, token_in[0]["mint"], _amount_field(token_in[0]), quote, at, venue="helius"))

    for transfer in tx.get("nativeTransfers") or []:
        src = transfer.get("fromUserAccount")
        dst = transfer.get("toUserAccount")
        if src and dst:
            amount = build.amount_from_raw(int(transfer["amount"]), _LAMPORT_DECIMALS)
            out.append(build.funding(src, dst, amount, at))

    return out


class HeliusSource:
    def __init__(
        self,
        payloads: Iterable[dict],
        *,
        now: Callable[[], Nanos] = now_nanos,
        name: str = "helius",
    ) -> None:
        self._payloads = payloads
        self._now = now
        self.name = name

    def event_stream(self) -> Iterator[SourcedEvent]:
        for tx in self._payloads:
            ingestion = self._now()  # receipt time — when we learned of it
            for payload in translate_helius(tx):
                yield SourcedEvent(payload=payload, ingestion_time=ingestion)


# The live network transport lives in wis.sources.helius_live, kept separate so
# the translation above stays pure and fully testable on its own.
