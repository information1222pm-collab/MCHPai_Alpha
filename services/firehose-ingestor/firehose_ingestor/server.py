"""FastAPI server — drives a firehose into the AlphaEngine and exposes it.

Endpoints
    GET  /health           liveness + ingest stats
    GET  /stats            engine stats (swaps, tokens, graded/proven wallets)
    GET  /signals          live multi-detector feed
    GET  /alpha            current top tokens by Alpha Score
    WS   /stream           pushes every parsed swap + periodic signal snapshots

Run:  python -m firehose_ingestor          (Helius if HELIUS_API_KEY set, else mock)
FastAPI/uvicorn/websockets are imported lazily so the engine stays testable
without the web stack installed.
"""

from __future__ import annotations

import asyncio
import json
import os
import time

from .engine import AlphaEngine
from .transport import HeliusWsFirehose, MockFirehose


def _demo_swaps() -> list[dict]:
    """A tiny synthetic stream so the server does something useful without a key."""
    now = int(time.time())
    out = []
    for i in range(12):
        out.append(dict(signature=f"d{i}", wallet=f"w{i%6}", mint="DEMOmint",
                        side="buy" if i % 4 else "sell", sol=0.6 + i * 0.1,
                        tok=1000, price=0.001 * (1 + i * 0.05), ts=now + i, dex="raydium_amm"))
    return out


def build_app():
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect

    follows = set()
    fpath = os.environ.get("FOLLOWS_FILE")
    if fpath and os.path.exists(fpath):
        with open(fpath) as fh:
            follows = {ln.strip() for ln in fh if ln.strip()}

    engine = AlphaEngine(follows=follows)
    app = FastAPI(title="MCHPAI firehose-ingestor")
    clients: set = set()
    state = {"started": time.time()}

    async def _broadcast(payload: dict):
        dead = []
        for ws in clients:
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                dead.append(ws)
        for ws in dead:
            clients.discard(ws)

    async def _consume():
        key = os.environ.get("HELIUS_API_KEY", "")
        if key:
            fh = HeliusWsFirehose(key, concurrency=int(os.environ.get("RPC_CONCURRENCY", "8")))
            state["source"] = "helius-ws"
        else:
            fh = MockFirehose(_demo_swaps(), delay=0.5)
            state["source"] = "mock (set HELIUS_API_KEY for the real firehose)"
        async for sw in fh.swaps():
            engine.ingest(sw)
            await _broadcast({"t": "swap", "swap": sw})

    async def _scanner():
        while True:
            await asyncio.sleep(7)
            engine.scan(engine.now or int(time.time()))
            await _broadcast({"t": "signals", "signals": engine.top_signals(20),
                              "stats": engine.stats()})

    @app.on_event("startup")
    async def _startup():
        app.state.tasks = [asyncio.create_task(_consume()), asyncio.create_task(_scanner())]

    @app.on_event("shutdown")
    async def _shutdown():
        for t in app.state.tasks:
            t.cancel()

    @app.get("/health")
    async def health():
        return {"ok": True, "uptime_s": round(time.time() - state["started"], 1),
                "source": state.get("source"), **engine.stats()}

    @app.get("/stats")
    async def stats():
        return engine.stats()

    @app.get("/signals")
    async def signals(n: int = 40):
        return {"signals": engine.top_signals(n), "counts": engine.counts}

    @app.get("/alpha")
    async def alpha(n: int = 12, min_score: float = 40.0):
        return {"alpha": engine.top_alpha(n, min_score)}

    @app.websocket("/stream")
    async def stream(ws: WebSocket):
        await ws.accept()
        clients.add(ws)
        try:
            await ws.send_text(json.dumps({"t": "hello", "stats": engine.stats()}))
            while True:
                await ws.receive_text()   # keepalive; we only push
        except WebSocketDisconnect:
            pass
        finally:
            clients.discard(ws)

    return app


def main():
    import uvicorn
    uvicorn.run(build_app(), host=os.environ.get("HOST", "0.0.0.0"),
                port=int(os.environ.get("PORT", "8787")))


if __name__ == "__main__":
    main()
