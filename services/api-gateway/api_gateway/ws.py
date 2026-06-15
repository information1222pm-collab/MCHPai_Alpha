"""WebSocket live feed — bridges NATS signals to browser clients.

Clients connect to ``/ws/live`` and receive prediction/buy-signal/cluster events
in real time. Each connection gets its own ephemeral NATS subscription so the
gateway stays stateless and horizontally scalable.
"""

from __future__ import annotations

import asyncio

import nats
import orjson
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from mchpai_common.config import settings
from mchpai_common.events.subjects import SIGNALS

router = APIRouter()


@router.websocket("/ws/live")
async def live_feed(ws: WebSocket) -> None:
    await ws.accept()
    nc = await nats.connect(settings.nats_url)
    queue: asyncio.Queue = asyncio.Queue(maxsize=1000)

    async def _on_msg(msg) -> None:
        try:
            queue.put_nowait(msg.data)
        except asyncio.QueueFull:
            pass  # drop under backpressure; this is a best-effort feed

    sub = await nc.subscribe(f"{SIGNALS}.>", cb=_on_msg)
    try:
        while True:
            data = await queue.get()
            await ws.send_bytes(data)
    except WebSocketDisconnect:
        pass
    finally:
        await sub.unsubscribe()
        await nc.drain()
