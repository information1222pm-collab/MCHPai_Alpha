"""prediction-engine entrypoint.

On each attention spike (or cluster detection), pull the token's feature vector,
compute the five scores, persist + cache the prediction, and emit
``PredictionGenerated`` — and ``BuySignalGenerated`` when the gate is crossed.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone

import orjson

from mchpai_common.config import settings
from mchpai_common.database import get_pg_pool, get_redis
from mchpai_common.events import Envelope, EventBus
from mchpai_common.events.subjects import ATTENTION_SPIKE, CLUSTER_DETECTED
from mchpai_common.events.types import BuySignalGenerated, EventType, PredictionGenerated
from mchpai_common.logging import configure as configure_logging, get_logger
from mchpai_common.metrics import BUY_SIGNALS, PREDICTION_LATENCY, start_metrics_server
from mchpai_common.schemas.scores import Prediction

from . import scoring
from .registry import ModelRegistry

SERVICE = "prediction-engine"
MODEL_VERSION = "baseline-v0"


async def load_features(rds, mint: str) -> dict[str, float]:
    raw = await rds.get(f"feat:vec:{mint}")
    return orjson.loads(raw) if raw else {}


async def persist_prediction(pool, pred: Prediction) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO predictions
              (mint, model_version, buy_probability, expected_value, risk_score, features)
            VALUES ($1,$2,$3,$4,$5,$6) RETURNING id
            """,
            pred.mint, pred.model_version, pred.buy_probability,
            pred.expected_value, pred.risk_score, pred.features,
        )
        return int(row["id"])


async def main() -> None:
    configure_logging(level=settings.log_level, fmt=settings.log_format, service=SERVICE)
    log = get_logger(SERVICE)
    start_metrics_server(settings.prometheus_port)

    pool = await get_pg_pool()
    rds = get_redis()
    registry = ModelRegistry()
    predict_buy = registry.load("buy_probability")
    bus = await EventBus(settings.nats_url, producer=SERVICE).connect()
    await bus.ensure_streams()

    async def evaluate(mint: str, extra: dict) -> None:
        t0 = time.perf_counter()
        features = await load_features(rds, mint)
        features.update(extra)

        bp = predict_buy(features)
        ev = scoring.expected_value_bps(bp)
        risk = float(features.get("risk_score", features.get("structural_risk", 40.0)))

        pred = Prediction(
            mint=mint, model_version=MODEL_VERSION, buy_probability=bp,
            expected_value=ev, risk_score=risk, features=features,
            created_at=datetime.now(timezone.utc),
        )
        PREDICTION_LATENCY.observe((time.perf_counter() - t0) * 1000)

        signal_id = await persist_prediction(pool, pred)
        await rds.set(f"pred:{mint}", pred.model_dump_json(), ex=120)
        await bus.publish(
            EventType.PREDICTION_GENERATED,
            PredictionGenerated(
                mint=mint, model_version=MODEL_VERSION, buy_probability=bp,
                expected_value=ev, risk_score=risk,
                top_cluster_id=extra.get("top_cluster_id"),
            ),
            partition_key=mint,
        )

        if pred.crosses(settings.tau_buy_probability, settings.tau_expected_value_bps,
                        settings.tau_risk_score_max):
            await bus.publish(
                EventType.BUY_SIGNAL_GENERATED,
                BuySignalGenerated(
                    signal_id=str(signal_id), mint=mint, size_sol=0.0,  # strategy sizes it
                    expected_value=ev, risk_score=risk, buy_probability=bp,
                ),
                partition_key=mint,
            )
            BUY_SIGNALS.inc()
            log.info("buy_signal", mint=mint, bp=round(bp, 3), ev=round(ev, 1), risk=round(risk, 1))

    async def on_attention(env: Envelope) -> None:
        p = env.payload
        await evaluate(p["mint"], {"attention.r0_norm": min(1.0, p.get("r0", 0.0) / 3.0)})

    async def on_cluster(env: Envelope) -> None:
        # A cluster forming around recently-bought mints is a strong precursor.
        p = env.payload
        score_norm = min(1.0, p.get("cluster_score", 0.0) / 100.0)
        # In production, map cluster → active mints; here we cache the cluster score.
        await rds.set(f"cluster:last_score", orjson.dumps({"score": score_norm}).decode(), ex=600)

    await bus.subscribe(ATTENTION_SPIKE, on_attention, durable=f"{SERVICE}.attention")
    await bus.subscribe(CLUSTER_DETECTED, on_cluster, durable=f"{SERVICE}.cluster")
    log.info("prediction-engine.started", model_version=MODEL_VERSION)
    await bus.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
