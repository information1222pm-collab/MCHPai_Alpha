"""RPCSource — the universal fallback via standard Solana JSON-RPC.

Plain ``getTransaction`` works against any RPC node, so this source is the
always-available fallback when Helius/Yellowstone are not. It has no decoded
swap object to lean on, so it *infers* a swap from balance deltas: how the
signer's token balance and SOL balance changed across the transaction. Token up
+ SOL down is a buy; token down + SOL up is a sell.

The inference is a pure function of a parsed transaction, hence testable in
process; the RPC transport is a thin lazy adapter. Verified against sample
transactions, pending verification against a live node. Fee handling is
intentionally simple (fees are not netted out) — a documented approximation we
refine once a live node confirms exact figures.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator

from wis.domain.events import DomainEvent
from wis.domain.time import Nanos, now_nanos
from wis.sources import build
from wis.sources.base import SourcedEvent

_LAMPORT_DECIMALS = 9


def _signer_token_delta(meta: dict, signer: str) -> tuple[str, int, int] | None:
    """Return (mint, delta_raw, decimals) for the signer's largest token change."""
    pre = {(b["owner"], b["mint"]): b for b in meta.get("preTokenBalances", [])}
    post = {(b["owner"], b["mint"]): b for b in meta.get("postTokenBalances", [])}
    best: tuple[str, int, int] | None = None
    for key in set(pre) | set(post):
        owner, mint = key
        if owner != signer:
            continue
        pre_amt = int(pre[key]["uiTokenAmount"]["amount"]) if key in pre else 0
        post_amt = int(post[key]["uiTokenAmount"]["amount"]) if key in post else 0
        decimals = int((post.get(key) or pre.get(key))["uiTokenAmount"]["decimals"])
        delta = post_amt - pre_amt
        if delta != 0 and (best is None or abs(delta) > abs(best[1])):
            best = (mint, delta, decimals)
    return best


def translate_rpc(tx: dict) -> list[DomainEvent]:
    """Pure: one parsed ``getTransaction`` result → zero or more domain events."""
    block_time = tx.get("blockTime")
    if block_time is None:
        return []
    at = int(block_time) * 1_000_000_000
    keys = tx["transaction"]["message"]["accountKeys"]
    signer = keys[0] if keys else None
    meta = tx.get("meta") or {}
    if signer is None or not meta:
        return []

    token = _signer_token_delta(meta, signer)
    if token is None:
        return []
    mint, token_delta, decimals = token

    pre_bal = meta.get("preBalances") or []
    post_bal = meta.get("postBalances") or []
    sol_delta = (post_bal[0] - pre_bal[0]) if pre_bal and post_bal else 0

    base = build.amount_from_raw(abs(token_delta), decimals)
    if token_delta > 0 and sol_delta < 0:  # received token, paid SOL -> buy
        quote = build.amount_from_raw(abs(sol_delta), _LAMPORT_DECIMALS)
        return [build.buy(signer, mint, base, quote, at, venue="rpc")]
    if token_delta < 0 and sol_delta > 0:  # sold token, received SOL -> sell
        quote = build.amount_from_raw(abs(sol_delta), _LAMPORT_DECIMALS)
        return [build.sell(signer, mint, base, quote, at, venue="rpc")]
    return []


class RPCSource:
    def __init__(
        self,
        transactions: Iterable[dict],
        *,
        now: Callable[[], Nanos] = now_nanos,
        name: str = "rpc",
    ) -> None:
        self._transactions = transactions
        self._now = now
        self.name = name

    def event_stream(self) -> Iterator[SourcedEvent]:
        for tx in self._transactions:
            ingestion = self._now()
            for payload in translate_rpc(tx):
                yield SourcedEvent(payload=payload, ingestion_time=ingestion)
