"""The read-only API builds and exposes the observatory surface. FastAPI is an
optional extra, so the test is skipped when it isn't installed."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from wis.app.observatory import Observatory  # noqa: E402
from wis.domain.events import WalletCreated  # noqa: E402
from wis.domain.identifiers import WalletAddress  # noqa: E402
from wis.domain.time import DAY, Nanos  # noqa: E402


def test_app_exposes_read_only_routes() -> None:
    from wis.app.api.server import create_app

    obs = Observatory()
    obs.ingest(WalletCreated(occurred_at=Nanos(DAY), wallet=WalletAddress("w")), ingestion_time=Nanos(DAY))
    app = create_app(obs)
    paths = {route.path for route in app.routes}  # type: ignore[attr-defined]
    assert {"/health", "/wallets", "/wallets/{address}", "/graph/summary", "/clusters"} <= paths


def test_endpoints_return_observed_data() -> None:
    from starlette.testclient import TestClient

    obs = Observatory()
    obs.ingest(WalletCreated(occurred_at=Nanos(DAY), wallet=WalletAddress("w")), ingestion_time=Nanos(DAY))
    from wis.app.api.server import create_app

    client = TestClient(create_app(obs))
    assert client.get("/health").json()["status"] == "ok"
    assert "w" in client.get("/wallets").json()["wallets"]
    assert client.get("/wallets/unknown").status_code == 404
