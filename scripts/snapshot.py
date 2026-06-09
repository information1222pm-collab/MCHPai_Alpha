#!/usr/bin/env python3
"""Export a self-contained snapshot of the Observation Center.

Bakes the current data into a single static HTML file (same dashboard UI, no
server required) so it can be opened directly in any browser or shared. Clearly
labeled as a point-in-time snapshot — for the live, auto-refreshing view, run
scripts/observatory.py.

    python scripts/snapshot.py            # -> data/observatory_snapshot.html
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import scripts.observatory as O


def collect() -> dict:
    snap = {
        "/api/stats": O.api_stats(),
        "/api/births": O.api_births(),
        "/api/top": O.api_top(),
        "/api/patterns": O.api_patterns(),
        "/api/ml": O.api_ml(),
        "/api/rl": O.api_rl(),
        "/api/wallets": O.api_wallets(),
    }
    for w in snap["/api/wallets"]:
        snap[f"/api/wallet?addr={w['wallet']}"] = O.api_wallet(w["wallet"])
    return snap


def build_html(snap: dict) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    page = O.PAGE
    # 1) replace fetch-based loader with an embedded-data lookup
    page = page.replace(
        "async function j(u){try{return await(await fetch(u)).json()}catch(e){return null}}",
        "async function j(u){return (window.SNAP&&window.SNAP[u]!==undefined)?window.SNAP[u]:null}",
    )
    # 2) single render (no auto-refresh in a static file)
    page = page.replace("tick();setInterval(tick,4000);", "tick();")
    # 3) inject the data and a SNAPSHOT label
    blob = json.dumps(snap).replace("</", "<\\/")
    page = page.replace("<script>", f"<script>window.SNAP={blob};</script>\n<script>", 1)
    page = page.replace("MCHPAI · OBSERVATION CENTER",
                        f"MCHPAI · OBSERVATION CENTER — SNAPSHOT {ts}")
    return page


def main() -> None:
    os.makedirs("data", exist_ok=True)
    html = build_html(collect())
    out = "data/observatory_snapshot.html"
    with open(out, "w") as f:
        f.write(html)
    print(f"wrote {out} ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
