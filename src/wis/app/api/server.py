"""The Observatory HTTP API — a Bloomberg-terminal-style read surface.

Strictly *read-only by intent*: it exposes what the system has observed and
concluded, never trading actions. Ingestion happens through the event backbone,
not through this API. FastAPI is an optional dependency (the ``api`` extra); the
core never imports this module.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from wis.app.observatory import Observatory
from wis.app.serializers import (
    graph_summary_to_dict,
    report_to_dict,
)
from wis.domain.identifiers import WalletAddress


def create_app(observatory: Observatory | None = None) -> FastAPI:
    obs = observatory if observatory is not None else Observatory()
    app = FastAPI(
        title="MCHPAI Advanced Wallet Intelligence System",
        description="The observatory: transform anonymous addresses into understandable entities.",
        version="0.1.0",
    )

    @app.get("/health")
    def health() -> dict[str, object]:
        return {"status": "ok", "events": int(obs.store.head)}

    @app.get("/wallets")
    def wallets() -> dict[str, object]:
        addrs = obs.list_wallets()
        return {"count": len(addrs), "wallets": [a.value for a in addrs]}

    @app.get("/wallets/{address}")
    def wallet(address: str) -> dict[str, object]:
        report = obs.wallet_report(WalletAddress(address))
        if report is None:
            raise HTTPException(status_code=404, detail=f"unknown wallet {address}")
        return report_to_dict(report)

    @app.get("/wallets/{address}/features")
    def wallet_features(address: str) -> dict[str, object]:
        report = obs.wallet_report(WalletAddress(address))
        if report is None:
            raise HTTPException(status_code=404, detail=f"unknown wallet {address}")
        return {k: v.value for k, v in report.features.values.items()}

    @app.get("/graph/summary")
    def graph_summary() -> dict[str, object]:
        return graph_summary_to_dict(obs.graph_summary())

    @app.get("/clusters")
    def clusters() -> dict[str, object]:
        cs = obs.clusters()
        return {
            "count": len(cs),
            "clusters": {cid.value: [w.value for w in members] for cid, members in cs.items()},
        }

    return app
