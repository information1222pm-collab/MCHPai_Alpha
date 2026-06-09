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
# Canonical rent-exempt minimum for a 165-byte SPL token account (lamports);
# appears constantly as a temporary ATA deposit/refund inside swaps.
ATA_RENT_LAMPORTS = 2_039_280

# Recognized quote assets. A token-to-token swap with exactly one quote leg is a
# real, priceable trade in that quote; quote↔quote is a currency conversion (not
# a speculative trade); token↔token with no quote leg is currently unpriceable.
# (See reality_lab/bug_journal.md BUG-001 and the Reality measurements.)
_WSOL = "So11111111111111111111111111111111111111112"
_QUOTE_SYMBOL = {
    _WSOL: "SOL",
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": "USDT",
}

# Native transfers that are swap/account mechanics, not genuine peer funding
# (BUG-002): below this they are dust (fees/tips); the exact rent constant and
# self-transfers are also mechanics. Funding is only emitted from non-swap
# transactions, and never for these.
_DUST_LAMPORTS = 100_000  # 0.0001 SOL


def _amount_field(token_obj: dict):
    raw = token_obj["rawTokenAmount"]
    return build.amount_from_raw(int(raw["tokenAmount"]), int(raw["decimals"]))


def _is_mechanics(amount: int, src: str | None, dst: str | None) -> bool:
    return src == dst or amount == ATA_RENT_LAMPORTS or amount < _DUST_LAMPORTS


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
        if native_in and token_out and not token_in:  # SOL spent, token received -> BUY
            quote = build.amount_from_raw(int(native_in["amount"]), _LAMPORT_DECIMALS)
            out.append(build.buy(wallet, token_out[0]["mint"], _amount_field(token_out[0]), quote, at, venue="helius"))
        elif token_in and native_out and not token_out:  # token spent, SOL received -> SELL
            quote = build.amount_from_raw(int(native_out["amount"]), _LAMPORT_DECIMALS)
            out.append(build.sell(wallet, token_in[0]["mint"], _amount_field(token_in[0]), quote, at, venue="helius"))
        elif token_in and token_out and not native_in and not native_out:
            # Token-to-token (router): a trade only if exactly one leg is a known
            # quote asset; quote↔quote is a conversion, token↔token is unpriceable.
            ti, to = token_in[0], token_out[0]
            in_q = _QUOTE_SYMBOL.get(ti.get("mint"))
            out_q = _QUOTE_SYMBOL.get(to.get("mint"))
            if in_q and not out_q:      # quote spent, token received -> BUY priced in `in_q`
                out.append(build.buy(wallet, to["mint"], _amount_field(to), _amount_field(ti), at,
                                     venue="helius", quote_mint=in_q))
            elif out_q and not in_q:    # token spent, quote received -> SELL priced in `out_q`
                out.append(build.sell(wallet, ti["mint"], _amount_field(ti), _amount_field(to), at,
                                      venue="helius", quote_mint=out_q))

    # Funding comes from transfers, not swaps; in a swap the native moves are
    # trade mechanics. Even in a transfer, drop dust / rent / self (BUG-002).
    if not swap:
        for transfer in tx.get("nativeTransfers") or []:
            src = transfer.get("fromUserAccount")
            dst = transfer.get("toUserAccount")
            amount = int(transfer.get("amount", 0))
            if src and dst and not _is_mechanics(amount, src, dst):
                out.append(build.funding(src, dst, build.amount_from_raw(amount, _LAMPORT_DECIMALS), at))

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
