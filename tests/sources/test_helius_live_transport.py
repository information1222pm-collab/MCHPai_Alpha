"""The Helius live transport is verified in-process against a SIMULATED Helius
API (httpx.MockTransport): pagination walks the ``before`` cursor and the window
is returned oldest-first, so the log sees buys before sells. Only a real socket
needs a real key."""

from __future__ import annotations

import pytest

httpx = pytest.importorskip("httpx")

from wis.sources.helius_live import HeliusLiveTransport, merge_time_ordered  # noqa: E402

# Master list as Helius serves it: newest-first.
_MASTER = [
    {"signature": "sig3", "timestamp": 300, "type": "OTHER"},
    {"signature": "sig2", "timestamp": 200, "type": "OTHER"},
    {"signature": "sig1", "timestamp": 100, "type": "OTHER"},
]


def _handler(request: httpx.Request) -> httpx.Response:
    assert request.url.params.get("api-key") == "test-key"
    limit = int(request.url.params.get("limit", "100"))
    before = request.url.params.get("before")
    if before is None:
        start = 0
    else:
        idx = next(i for i, tx in enumerate(_MASTER) if tx["signature"] == before)
        start = idx + 1
    return httpx.Response(200, json=_MASTER[start : start + limit])


def _transport() -> HeliusLiveTransport:
    client = httpx.Client(transport=httpx.MockTransport(_handler))
    return HeliusLiveTransport("test-key", client=client)


def test_pagination_returns_oldest_first() -> None:
    txs = _transport().transactions("addr", limit=2, max_pages=10)
    assert [t["signature"] for t in txs] == ["sig1", "sig2", "sig3"]
    assert [t["timestamp"] for t in txs] == [100, 200, 300]


def test_single_page_when_fewer_than_limit() -> None:
    txs = _transport().transactions("addr", limit=100, max_pages=10)
    assert [t["signature"] for t in txs] == ["sig1", "sig2", "sig3"]


def test_merge_time_orders_multiple_wallets() -> None:
    a = [{"signature": "a2", "timestamp": 200}, {"signature": "a1", "timestamp": 100}]
    b = [{"signature": "b1", "timestamp": 150}]
    merged = merge_time_ordered([a, b])
    assert [t["timestamp"] for t in merged] == [100, 150, 200]
