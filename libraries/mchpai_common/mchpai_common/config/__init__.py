"""Centralized, typed configuration for every MCHPAI service.

Single source of truth read from environment (12-factor). Services do
``from mchpai_common.config import settings`` and never touch ``os.environ``
directly, so configuration is typed, validated, and discoverable.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # runtime
    mchpai_env: str = "local"
    log_level: str = "INFO"
    log_format: str = "json"

    # event bus
    nats_url: str = "nats://nats:4222"
    nats_stream_prefix: str = "mchpai"
    nats_durable_prefix: str = "mchpai"

    # datastores
    postgres_url: str = "postgresql://mchpai:mchpai_dev_pw@postgres:5432/mchpai"
    clickhouse_host: str = "clickhouse"
    clickhouse_port: int = 9000
    clickhouse_http_port: int = 8123
    clickhouse_db: str = "mchpai"
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "mchpai_dev_pw"
    redis_url: str = "redis://redis:6379/0"

    # object store
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "mchpai"
    minio_secret_key: str = "mchpai_dev_secret"
    minio_bucket_features: str = "features"
    minio_bucket_models: str = "models"
    minio_secure: bool = False

    # providers
    helius_api_key: str = ""
    helius_rpc_url: str = ""
    birdeye_api_key: str = ""
    jupiter_api_url: str = "https://quote-api.jup.ag/v6"
    yellowstone_endpoint: str = ""
    yellowstone_x_token: str = ""

    # execution / risk
    execution_mode: str = "paper"
    jito_block_engine_url: str = "https://mainnet.block-engine.jito.wtf"
    jito_tip_lamports: int = 100_000
    bankroll_sol: float = 10.0
    kelly_fraction: float = 0.25
    min_ticket_sol: float = 0.05
    max_ticket_sol: float = 2.0
    max_token_exposure_sol: float = 4.0
    daily_loss_limit_sol: float = 3.0

    # prediction thresholds
    tau_buy_probability: float = 0.65
    tau_expected_value_bps: float = 150
    tau_risk_score_max: float = 55

    # alerts
    discord_webhook_url: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # observability
    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"
    prometheus_port: int = Field(default=9000)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
