"""Firehose transports — the source of the full swap stream.

A transport is an async iterator of normalized swap dicts. Three are provided:

* ``MockFirehose``      — replays a fixed list; offline, used by tests.
* ``HeliusWsFirehose``  — Helius WebSocket ``logsSubscribe`` on the DEX program
                          ids (the accessible full firehose: every tx touching
                          those programs), then ``getTransaction`` → parse.
* ``YellowstoneFirehose`` — stub for the true Geyser/LaserStream gRPC firehose
                          (lowest latency, paid plan). Documented upgrade path.

Swapping transports does not touch the engine — same swap dicts flow in.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from mchpai_common.parsing.program_ids import DEX_BY_PROGRAM

from .rpc import HeliusRpc, swaps_from_jsonparsed

# The concrete DEX programs whose firehose we subscribe to (skip the Jupiter router).
DEX_PROGRAMS = [pid for pid, dex in DEX_BY_PROGRAM.items() if dex.value != "jupiter"]


class Firehose:
    async def swaps(self) -> AsyncIterator[dict]:
        raise NotImplementedError
        yield  # pragma: no cover

    async def close(self) -> None:
        pass


class MockFirehose(Firehose):
    """Replays a fixed list of swap dicts (optionally with a small delay)."""

    def __init__(self, swaps: list[dict], delay: float = 0.0):
        self._swaps = swaps
        self._delay = delay

    async def swaps(self) -> AsyncIterator[dict]:
        for sw in self._swaps:
            if self._delay:
                await asyncio.sleep(self._delay)
            yield sw


class HeliusWsFirehose(Firehose):
    """Subscribe to DEX program logs over Helius WS, resolve + parse each tx.

    NOTE: high-throughput. A semaphore bounds concurrent getTransaction calls so
    we don't exhaust RPC credits; tune ``concurrency`` to your plan. Signatures
    are de-duplicated. Reconnects automatically on socket close.
    """

    def __init__(self, api_key: str, programs: list[str] | None = None,
                 concurrency: int = 8, commitment: str = "processed"):
        self.api_key = api_key
        self.programs = programs or DEX_PROGRAMS
        self.rpc = HeliusRpc(api_key)
        self._sem = asyncio.Semaphore(concurrency)
        self._seen: set[str] = set()
        self._commitment = commitment
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self._closed = False

    async def _resolve(self, sig: str):
        async with self._sem:
            res = await self.rpc.get_transaction(sig)
        if res:
            for sw in swaps_from_jsonparsed(res):
                await self._queue.put(sw)

    async def _reader(self):
        import json
        import websockets  # lazy: deploy-only dependency
        url = f"wss://mainnet.helius-rpc.com/?api-key={self.api_key}"
        while not self._closed:
            try:
                async with websockets.connect(url, max_size=None, ping_interval=20) as ws:
                    sub_id = 1
                    for pid in self.programs:
                        await ws.send(json.dumps({
                            "jsonrpc": "2.0", "id": sub_id, "method": "logsSubscribe",
                            "params": [{"mentions": [pid]}, {"commitment": self._commitment}],
                        }))
                        sub_id += 1
                    async for raw in ws:
                        msg = json.loads(raw)
                        if msg.get("method") != "logsNotification":
                            continue
                        val = (msg.get("params") or {}).get("result", {}).get("value", {})
                        sig = val.get("signature")
                        if sig and not val.get("err") and sig not in self._seen:
                            self._seen.add(sig)
                            if len(self._seen) > 200000:
                                self._seen.clear()
                            asyncio.create_task(self._resolve(sig))
            except Exception:
                if self._closed:
                    break
                await asyncio.sleep(3)

    async def swaps(self) -> AsyncIterator[dict]:
        reader = asyncio.create_task(self._reader())
        try:
            while not self._closed:
                sw = await self._queue.get()
                yield sw
        finally:
            reader.cancel()

    async def close(self) -> None:
        self._closed = True
        await self.rpc.close()


class YellowstoneFirehose(Firehose):
    """Stub for the Yellowstone Geyser / Helius LaserStream gRPC firehose.

    The true firehose: every account/transaction update streamed via gRPC with
    the lowest possible latency (no per-tx getTransaction round-trip). Requires a
    paid plan + generated protobuf stubs (``yellowstone-grpc-proto``). To wire:

      1. pip install grpcio grpcio-tools and generate stubs from geyser.proto
      2. connect to the LaserStream endpoint with the x-token auth metadata
      3. SubscribeRequest filtering transactions by ``account_include`` =
         DEX_PROGRAMS, map each update's meta into a TxContext (same fields the
         jsonParsed path uses) and yield ``swaps_from_*``.

    Left as a documented seam so the rest of the service is gRPC-ready without
    pulling the heavy dependency into the accessible WebSocket path.
    """

    def __init__(self, endpoint: str, token: str, programs: list[str] | None = None):
        self.endpoint = endpoint
        self.token = token
        self.programs = programs or DEX_PROGRAMS

    async def swaps(self) -> AsyncIterator[dict]:
        raise NotImplementedError(
            "Yellowstone gRPC firehose not wired — generate geyser protobuf stubs "
            "and a paid LaserStream endpoint, then map updates to swap dicts. "
            "Use HeliusWsFirehose for the WebSocket firehose in the meantime."
        )
        yield  # pragma: no cover
