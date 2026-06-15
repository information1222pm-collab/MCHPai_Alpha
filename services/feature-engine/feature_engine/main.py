"""feature-engine entrypoint.

Now powered by the **Feature Factory**: a declarative catalog compiled once into a
single callable that emits hundreds of features per snapshot. Maintains a bounded
per-mint history so rolling/windowed transforms are correct and causal, writes the
vector to ClickHouse (offline) + Redis (online), and emits ``AttentionSpike`` on
virality.
"""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict, deque
from datetime import datetime, timezone

import orjson

from mchpai_common.config import settings
from mchpai_common.database import get_clickhouse, get_redis
from mchpai_common.events import Envelope, EventBus
from mchpai_common.events.subjects import TOKEN_SNAPSHOT
from mchpai_common.events.types import AttentionSpike, EventType
from mchpai_common.feature_factory import FeatureCompiler, FeatureContext, build_default_catalog
from mchpai_common.logging import configure as configure_logging, get_logger
from mchpai_common.metrics import FEATURE_COMPUTE_LATENCY, start_metrics_server

SERVICE = "feature-engine"
HISTORY = 32          # rolling window depth kept per mint
MAX_MINTS = 100_000   # bounded resident history (LRU)
ATTENTION_VELOCITY_THRESHOLD = 0.5


def _row_from_event(p: dict) -> dict:
    """Map a TokenSnapshot event payload to the Factory's raw input row."""
    return {
        "price_sol": p.get("price_sol") or 0.0,
        "volume_sol": p.get("volume_1m") or 0.0,
        "liquidity_sol": p.get("liquidity_sol") or 0.0,
        "market_cap_sol": p.get("market_cap_sol") or 0.0,
        "buyers": p.get("buys_1m") or 0.0,
        "sellers": p.get("sells_1m") or 0.0,
        "unique_traders": p.get("unique_traders") or 0.0,
        "holders": p.get("holders") or 0.0,
        "txns": p.get("txns") or 0.0,
        "net_flow_sol": p.get("net_flow_sol") or 0.0,
        "entropy": p.get("entropy") or 0.0,
        "smart_money_ratio": p.get("smart_money_ratio") or 0.0,
        "cluster_ratio": p.get("cluster_ratio") or 0.0,
    }


class _History(OrderedDict):
    def get_buf(self, mint: str) -> deque:
        if mint in self:
            self.move_to_end(mint)
            return self[mint]
        buf: deque = deque(maxlen=HISTORY)
        self[mint] = buf
        if len(self) > MAX_MINTS:
            self.popitem(last=False)
        return buf


async def main() -> None:
    configure_logging(level=settings.log_level, fmt=settings.log_format, service=SERVICE)
    log = get_logger(SERVICE)
    start_metrics_server(settings.prometheus_port)

    rds = get_redis()
    ch = get_clickhouse()
    compiler = FeatureCompiler(build_default_catalog())
    history = _History()
    bus = await EventBus(settings.nats_url, producer=SERVICE).connect()
    await bus.ensure_streams()
    log.info("feature-engine.factory_loaded", features=len(compiler.feature_names))

    async def on_snapshot(env: Envelope) -> None:
        p = env.payload
        mint = p.get("mint")
        if not mint:
            return
        row = _row_from_event(p)
        buf = history.get_buf(mint)

        t0 = time.perf_counter()
        features = compiler.compute(FeatureContext(inputs=row, history=list(buf)))
        FEATURE_COMPUTE_LATENCY.observe((time.perf_counter() - t0) * 1000)
        buf.append(row)

        await rds.set(f"feat:vec:{mint}", orjson.dumps(features).decode(), ex=3600)
        try:
            ch.insert(
                "feature_vectors",
                [[datetime.now(timezone.utc), "token", mint, "factory", features]],
                column_names=["ts", "entity_type", "entity_id", "feature_set", "features"],
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("clickhouse.insert_failed", error=str(exc))

        vel = features.get("price_sol.rate_of_change.w5", 0.0)
        if vel >= ATTENTION_VELOCITY_THRESHOLD:
            await bus.publish(
                EventType.ATTENTION_SPIKE,
                AttentionSpike(
                    mint=mint,
                    attention=features.get("volume_sol.rolling_sum.w10", 0.0),
                    velocity=vel,
                    entropy=features.get("raw.entropy", 0.0),
                    r0=features.get("epi.r0_buyers.w10", 0.0),
                ),
                partition_key=mint,
            )

    await bus.subscribe(TOKEN_SNAPSHOT, on_snapshot, durable=f"{SERVICE}.snapshot")
    log.info("feature-engine.started")
    await bus.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
