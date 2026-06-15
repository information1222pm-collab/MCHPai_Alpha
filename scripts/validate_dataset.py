#!/usr/bin/env python3
"""Dataset validator — "does reality agree?".

Runs the integrity + quality checks from ``mchpai_common.quality`` against the
live stores, builds a :class:`DatasetQualityReport`, writes it to Redis
``quality:report`` (surfaced at ``GET /quality``), and prints it.

Usage:
    python scripts/validate_dataset.py            # full run against stores
    python scripts/validate_dataset.py --selfcheck  # code-level checks only (no stores)

The ``--selfcheck`` mode validates the *deployed code* (feature causality + reducer
replay determinism) with synthetic data and needs no infrastructure — safe to run
in CI and locally.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone

from mchpai_common.feature_factory import FeatureCompiler, build_default_catalog
from mchpai_common.quality import (
    DatasetQualityReport,
    assert_causal,
    replay_consistent,
)


def _code_level_checks(report: DatasetQualityReport) -> None:
    """Validate the deployed catalog + reducers (no stores needed)."""
    # 1) feature causality (no leakage) on the real catalog
    compiler = FeatureCompiler(build_default_catalog())
    rows = [
        {m: float(i + 1) for m in (
            "price_sol", "volume_sol", "liquidity_sol", "market_cap_sol", "buyers",
            "sellers", "unique_traders", "holders", "txns", "net_flow_sol",
            "entropy", "smart_money_ratio", "cluster_ratio")}
        for i in range(12)
    ]
    causal = assert_causal(compiler, rows)
    report.feature_leakage = not causal

    # 2) reducer replay determinism on a synthetic wallet stream
    from mchpai_common.schemas.common import Side
    from mchpai_common.schemas.swap import Dex, SwapEvent
    from mchpai_common.timelines import WalletStateReducer

    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = [
        SwapEvent(signature=f"s{i}", slot=i, timestamp=t0 + timedelta(seconds=i),
                  dex=Dex.unknown, wallet_address="W", token_address="M",
                  side=Side.buy if i % 2 == 0 else Side.sell,
                  sol_amount=1.0 + i, token_amount=100.0, price=0.01)
        for i in range(20)
    ]
    report.replay_deterministic = replay_consistent(
        events, lambda: WalletStateReducer("W"), lambda r, e: r.apply(e)
    )
    report.details["code_level"] = {"causal": causal,
                                    "replay_deterministic": report.replay_deterministic}


def _store_level_checks(report: DatasetQualityReport) -> None:  # pragma: no cover - I/O
    """Query the live stores. Each check is defensive: a store error becomes a
    detail note, never a crash."""
    from mchpai_common.database import get_clickhouse, get_redis
    import asyncio
    import asyncpg
    from mchpai_common.config import settings

    ch = get_clickhouse()
    rds = get_redis()

    # duplicate births (must be 0)
    try:
        res = ch.query(
            "SELECT count() AS n, uniqExact(JSONExtractString(payload,'mint')) AS u "
            "FROM event_log WHERE event_type = 'TokenCreated'"
        )
        n, u = res.result_rows[0]
        report.duplicate_births = max(0, int(n) - int(u))
    except Exception as e:
        report.details["duplicate_births_error"] = str(e)

    # snapshot skew: duplicate (mint,window,seq) tuples
    try:
        res = ch.query(
            "SELECT count() AS n, uniqExact((mint, window, seq)) AS u FROM snapshots"
        )
        n, u = res.result_rows[0]
        report.snapshot_skew = max(0, int(n) - int(u))
    except Exception as e:
        report.details["snapshot_skew_error"] = str(e)

    # slot-gap backlog (engine-published counters, if present)
    try:
        report.total_slot_gap = int(rds.get("ingest:total_slot_gap") or 0)
    except Exception:
        pass

    # label maturity + counters via Postgres/Redis
    async def _pg() -> None:
        try:
            conn = await asyncpg.connect(settings.postgres_url)
            row = await conn.fetchrow(
                "SELECT avg(CASE WHEN is_final THEN 1 ELSE 0 END)::float AS m FROM ground_truth"
            )
            report.label_maturity = float(row["m"] or 0.0)
            await conn.close()
        except Exception as e:
            report.details["pg_error"] = str(e)

    asyncio.get_event_loop().run_until_complete(_pg())

    # publish the report for /quality
    try:
        rds.set("quality:report", json.dumps(report.to_dict()))
    except Exception as e:
        report.details["publish_error"] = str(e)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true", help="code-level checks only")
    args = ap.parse_args()

    report = DatasetQualityReport()
    _code_level_checks(report)
    if not args.selfcheck:
        _store_level_checks(report)

    out = report.to_dict()
    print(json.dumps(out, indent=2))
    # non-zero exit on RED so cron/CI can alert
    return 0 if out["status"] != "RED" else 2


if __name__ == "__main__":
    sys.exit(main())
