"""Helius First Light — the live transport, and the proof reality is replayable.

This is the moment reality enters the system. Simplicity over performance:
plain HTTPS against Helius Enhanced Transactions, no Geyser, no gRPC, no
low-latency machinery. We need truth, and Helius is enough.

    Helius API → translate_helius() → Domain Events → Event Log → Replay → wallet_state(t)

The transport is deliberately thin and *injectable*: it takes an ``httpx``
client, so the pagination/ordering logic is verified in-process against a
simulated Helius API (``httpx.MockTransport``) and needs a real key only for an
actual socket. Everything else — translate, ingest, capture, replay, verify — is
the pure pipeline already proven elsewhere.

The headline guarantee (:func:`first_light`):

    live feed → JSONL archive → ArchiveSource → replay → digest
    must equal the live digest, bit-identically.

Once that holds, a non-deterministic live session becomes a perfectly
reproducible recording. That is extraordinarily valuable: reality itself becomes
replayable.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wis.conformance import wallet_world_digest
from wis.domain.identifiers import WalletAddress
from wis.domain.time import Nanos, now_nanos
from wis.eventsourcing.replay import ReplayEngine
from wis.eventsourcing.store import InMemoryEventStore
from wis.projections.wallet_projector import WalletProjector
from wis.sources.archive_source import ArchiveSource, capture, write_jsonl
from wis.sources.base import pump
from wis.sources.helius_source import HeliusSource

_DEFAULT_BASE = "https://api.helius.xyz"


class HeliusLiveTransport:
    """Pages Helius Enhanced Transactions for an address into raw payload dicts.

    Helius returns transactions newest-first; we page backwards with the
    ``before`` cursor and return the whole window **oldest-first**, so append
    order matches world order and the FIFO ledger sees buys before their sells.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = _DEFAULT_BASE,
        client: Any = None,
        max_retries: int = 4,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._client = client  # injectable httpx.Client; created lazily if None

    def _http(self):
        if self._client is None:
            import httpx  # lazy

            self._client = httpx.Client(timeout=self._timeout)
        return self._client

    def _get(self, address: str, before: str | None, limit: int) -> list[dict]:
        params = {"api-key": self._api_key, "limit": limit}
        if before:
            params["before"] = before
        url = f"{self._base_url}/v0/addresses/{address}/transactions"
        backoff = 2.0
        for attempt in range(self._max_retries + 1):
            resp = self._http().get(url, params=params)
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < self._max_retries:
                time.sleep(backoff)
                backoff *= 2
                continue
            resp.raise_for_status()
            return resp.json()
        return []

    def transactions(self, address: str, *, limit: int = 100, max_pages: int = 10) -> list[dict]:
        """Return up to ``limit * max_pages`` recent transactions, oldest-first."""
        collected: list[dict] = []
        before: str | None = None
        for _ in range(max_pages):
            batch = self._get(address, before, limit)
            if not batch:
                break
            collected.extend(batch)
            before = batch[-1].get("signature")
            if not before or len(batch) < limit:
                break
        collected.reverse()  # newest-first across pages → oldest-first
        return collected


def merge_time_ordered(payload_lists: Iterable[Iterable[dict]]) -> list[dict]:
    """Merge several wallets' transactions into one globally time-ordered stream.

    Sorted by ``(timestamp, signature)`` so the order is deterministic and a sell
    never precedes its buy across the merged log."""
    merged = [tx for lst in payload_lists for tx in lst]
    merged.sort(key=lambda tx: (int(tx.get("timestamp", 0)), str(tx.get("signature", ""))))
    return merged


def observe_wallets(
    transport: HeliusLiveTransport,
    addresses: Iterable[str],
    *,
    limit: int = 100,
    max_pages: int = 10,
) -> list[dict]:
    """Observe one or many wallets, returning a single time-ordered payload stream."""
    return merge_time_ordered(
        transport.transactions(addr, limit=limit, max_pages=max_pages) for addr in addresses
    )


@dataclass(frozen=True, slots=True)
class FirstLightResult:
    events_observed: int
    wallets: tuple[str, ...]
    live_digest: str
    replay_digest: str
    archive_path: str

    @property
    def replayable(self) -> bool:
        """The whole point: the archived recording replays to identical state."""
        return self.live_digest == self.replay_digest


def first_light(
    payloads: Iterable[dict],
    archive_path: str | Path,
    *,
    now: Callable[[], Nanos] = now_nanos,
) -> tuple[FirstLightResult, InMemoryEventStore]:
    """Run the full pipeline and prove the live recording is replayable.

    Takes raw Helius payloads (from the live transport, or a capture, or a test),
    ingests them through ``translate_helius`` into a log, archives the observed
    events, replays the archive into a fresh log, and compares digests. Returns
    the result and the live store (for inspecting ``wallet_state(t)``).
    """
    archive_path = Path(archive_path)

    # 1) Live: translate + ingest into the log (ingestion stamped at receipt).
    live_store = InMemoryEventStore()
    n = pump(HeliusSource(list(payloads), now=now), live_store)

    # 2) Capture the observed events to a durable archive.
    write_jsonl(capture(live_store), archive_path)

    # 3) Replay the archive into a fresh log.
    replay_store = InMemoryEventStore()
    pump(ArchiveSource(archive_path), replay_store)

    # 4) Compare wallet_state(t) digests — must be bit-identical.
    live_world = ReplayEngine(live_store, WalletProjector()).run()
    replay_world = ReplayEngine(replay_store, WalletProjector()).run()
    wallets = tuple(sorted(w.value for w in live_world.wallets))

    result = FirstLightResult(
        events_observed=n,
        wallets=wallets,
        live_digest=wallet_world_digest(live_world),
        replay_digest=wallet_world_digest(replay_world),
        archive_path=str(archive_path),
    )
    return result, live_store


def _print_observation(result: FirstLightResult, store: InMemoryEventStore) -> None:
    """Pure observation — facts only. No alpha, no scores, no prediction."""
    world = ReplayEngine(store, WalletProjector()).run()
    print("=" * 72)
    print(" Helius First Light — reality observed")
    print("=" * 72)
    print(f"\nEvents observed: {result.events_observed}   Wallets: {len(result.wallets)}")
    print(f"Archive: {result.archive_path}")
    status = "YES ✓" if result.replayable else "NO ✗"
    print(f"Replayable (live digest == archive replay): {status}")
    print(f"  live   : {result.live_digest}")
    print(f"  replay : {result.replay_digest}\n")

    for addr in result.wallets:
        ws = world.wallets.get(WalletAddress(addr))
        if ws is None:
            continue
        frame = ws.frame(prices=world.prices)
        p = frame.performance
        roi = f"{p.lifetime_roi:.2%}" if p.lifetime_roi is not None else "n/a"
        print(f"── wallet {addr} ──")
        print(f"   closed trades: {frame.sample_size}   open positions: {len(ws.open_positions())}")
        print(f"   lifetime ROI : {roi}")
        print(f"   DNA          : {frame.dna.summary()}\n")


def _main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="wis.sources.helius_live",
        description="Helius First Light: observe real wallet(s), archive, and prove replayability.",
    )
    parser.add_argument("--api-key", required=True, help="Helius API key")
    parser.add_argument("--wallet", action="append", required=True, dest="wallets", help="wallet address (repeatable)")
    parser.add_argument("--out", default="first_light.jsonl", help="archive output path (JSONL)")
    parser.add_argument("--limit", type=int, default=100, help="transactions per page")
    parser.add_argument("--max-pages", type=int, default=5, help="pages per wallet")
    parser.add_argument("--base-url", default=_DEFAULT_BASE, help="Helius base URL")
    args = parser.parse_args(argv)

    transport = HeliusLiveTransport(args.api_key, base_url=args.base_url)
    payloads = observe_wallets(transport, args.wallets, limit=args.limit, max_pages=args.max_pages)
    result, store = first_light(payloads, args.out)
    _print_observation(result, store)
    return 0 if result.replayable else 1


if __name__ == "__main__":
    raise SystemExit(_main())
