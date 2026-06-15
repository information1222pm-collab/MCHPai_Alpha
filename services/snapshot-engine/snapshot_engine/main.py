"""snapshot-engine entrypoint."""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timezone

from mchpai_common.config import settings
from mchpai_common.database import get_clickhouse, get_pg_pool, get_redis
from mchpai_common.epidemiology import estimate_r0
from mchpai_common.events import Envelope, EventBus
from mchpai_common.events.subjects import TOKEN_CREATED, WALLET_BOUGHT, WALLET_SOLD
from mchpai_common.events.types import EventType, TokenSnapshotEvent
from mchpai_common.logging import configure as configure_logging, get_logger
from mchpai_common.schemas.common import Side
from mchpai_common.schemas.snapshot import TokenSnapshot
from mchpai_common.schemas.swap import Dex, SwapEvent
from mchpai_common.snapshots import MultiWindowAggregator
from mchpai_common.snapshots.lifecycle import classify_phase

SERVICE = "snapshot-engine"
ALPHA_REFRESH_SECONDS = 120
IDLE_FLUSH_SECONDS = 90

CH_COLUMNS = [
    "ts", "mint", "window", "seq", "age_seconds", "phase",
    "price_sol", "open_sol", "high_sol", "low_sol", "close_sol", "volume_sol",
    "liquidity_sol", "market_cap_sol", "buyers", "sellers", "unique_traders",
    "holders", "txns", "entropy", "r0", "smart_money_ratio", "cluster_ratio",
    "net_flow_sol", "top_holder_pct", "holder_concentration_gini", "lp_health",
]


class SnapshotState:
    """Per-mint aggregation + running peaks + buyer history for R0."""

    def __init__(self, mint: str, birth: datetime, alpha_lookup) -> None:
        self.agg = MultiWindowAggregator(mint, birth, alpha_lookup=alpha_lookup)
        self.peak_liq = 0.0
        self.peak_px = 0.0
        self.buyer_hist: dict[str, deque] = {}
        self.last_swap_ts = birth


def _row(s: TokenSnapshot) -> list:
    return [
        s.ts, s.mint, s.window.value, s.seq, s.age_seconds, (s.phase.value if s.phase else ""),
        s.price_sol or 0.0, s.open_sol or 0.0, s.high_sol or 0.0, s.low_sol or 0.0,
        s.close_sol or 0.0, s.volume_sol, s.liquidity_sol or 0.0, s.market_cap_sol or 0.0,
        s.buyers, s.sellers, s.unique_traders, s.holders or 0, s.txns,
        s.entropy or 0.0, s.r0 or 0.0, s.smart_money_ratio or 0.0, s.cluster_ratio or 0.0,
        s.net_flow_sol, s.top_holder_pct or 0.0, s.holder_concentration_gini or 0.0,
        s.lp_health or 0.0,
    ]


async def main() -> None:
    configure_logging(level=settings.log_level, fmt=settings.log_format, service=SERVICE)
    log = get_logger(SERVICE)
    pool = await get_pg_pool()
    rds = get_redis()
    ch = get_clickhouse()
    bus = await EventBus(settings.nats_url, producer=SERVICE).connect()
    await bus.ensure_streams()

    alpha_cache: dict[str, float] = {}
    states: dict[str, SnapshotState] = {}

    def alpha_lookup(addr: str) -> float:
        return alpha_cache.get(addr, 0.0)

    async def refresh_alpha() -> None:
        while True:
            try:
                async with pool.acquire() as conn:
                    rows = await conn.fetch(
                        "SELECT address, wallet_alpha_score FROM wallet_scores "
                        "WHERE wallet_alpha_score IS NOT NULL"
                    )
                alpha_cache.clear()
                alpha_cache.update({r["address"]: float(r["wallet_alpha_score"]) for r in rows})
            except Exception as exc:  # noqa: BLE001
                log.warning("alpha_refresh.failed", error=str(exc))
            await asyncio.sleep(ALPHA_REFRESH_SECONDS)

    async def birth_of(mint: str, fallback: datetime) -> datetime:
        cached = await rds.get(f"birth:{mint}")
        if cached:
            return datetime.fromtimestamp(float(cached), tz=timezone.utc)
        await rds.set(f"birth:{mint}", str(fallback.timestamp()))
        return fallback

    async def emit_snapshots(st: SnapshotState, completed: dict) -> None:
        rows = []
        for window, snaps in completed.items():
            hist = st.buyer_hist.setdefault(window.value, deque(maxlen=12))
            for snap in snaps:
                # R0 from the running new-buyers series for this window
                hist.append(float(snap.buyers))
                if len(hist) >= 2:
                    import numpy as np
                    snap.r0 = estimate_r0(np.array(hist, dtype=float))
                # phase from running peaks
                if snap.liquidity_sol:
                    st.peak_liq = max(st.peak_liq, snap.liquidity_sol)
                if snap.price_sol:
                    st.peak_px = max(st.peak_px, snap.price_sol)
                snap.phase = classify_phase(
                    snap, peak_liquidity=st.peak_liq or None, peak_price=st.peak_px or None
                )
                rows.append(_row(snap))
                await bus.publish(
                    EventType.TOKEN_SNAPSHOT,
                    TokenSnapshotEvent(
                        mint=snap.mint, ts=snap.ts, price_sol=snap.price_sol,
                        liquidity_sol=snap.liquidity_sol, holders=snap.holders,
                        volume_1m=snap.volume_sol, buys_1m=snap.buyers, sells_1m=snap.sellers,
                    ),
                    partition_key=snap.mint,
                )
        if rows:
            try:
                ch.insert("snapshots", rows, column_names=CH_COLUMNS)
            except Exception as exc:  # noqa: BLE001
                log.warning("clickhouse.insert_failed", error=str(exc))

    async def on_swap(env: Envelope, side: Side) -> None:
        p = env.payload
        mint = p["mint"]
        ts = datetime.fromisoformat(p["block_time"]) if p.get("block_time") else datetime.now(timezone.utc)
        st = states.get(mint)
        if st is None:
            birth = await birth_of(mint, ts)
            st = SnapshotState(mint, birth, alpha_lookup)
            states[mint] = st
        st.last_swap_ts = ts
        swap = SwapEvent(
            signature=p.get("signature", ""), slot=p.get("slot") or 0, timestamp=ts,
            dex=Dex.unknown, wallet_address=p["wallet"], token_address=mint, side=side,
            sol_amount=float(p.get("sol_amount", 0)), token_amount=float(p.get("token_amount", 0)),
            price=p.get("price_sol"),
        )
        completed = st.agg.add(swap)
        if any(completed.values()):
            await emit_snapshots(st, completed)

    async def on_token_created(env: Envelope) -> None:
        p = env.payload
        ts = p.get("created_at")
        when = datetime.fromisoformat(ts) if ts else datetime.now(timezone.utc)
        await rds.set(f"birth:{p['mint']}", str(when.timestamp()))

    async def idle_flusher() -> None:
        while True:
            await asyncio.sleep(IDLE_FLUSH_SECONDS)
            now = datetime.now(timezone.utc)
            for mint, st in list(states.items()):
                if (now - st.last_swap_ts).total_seconds() > IDLE_FLUSH_SECONDS:
                    await emit_snapshots(st, st.agg.flush())
                    if (now - st.last_swap_ts).total_seconds() > 3600:
                        states.pop(mint, None)  # release dead tokens

    await bus.subscribe(TOKEN_CREATED, on_token_created, durable=f"{SERVICE}.created")
    await bus.subscribe(WALLET_BOUGHT, lambda e: on_swap(e, Side.buy), durable=f"{SERVICE}.bought")
    await bus.subscribe(WALLET_SOLD, lambda e: on_swap(e, Side.sell), durable=f"{SERVICE}.sold")
    log.info("snapshot-engine.started")
    await asyncio.gather(refresh_alpha(), idle_flusher())


if __name__ == "__main__":
    asyncio.run(main())
