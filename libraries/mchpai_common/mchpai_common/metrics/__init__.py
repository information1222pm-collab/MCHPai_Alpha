"""Prometheus metrics helpers shared by all services.

Provides the canonical platform metrics (events, latency, signals, discoveries)
and ``start_metrics_server`` so every service exposes ``/metrics`` identically.
Metric names are namespaced ``mchpai_*`` so Grafana dashboards are portable.
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram, start_http_server

# ---- platform-wide metrics -------------------------------------------------
EVENTS_PUBLISHED = Counter(
    "mchpai_events_published_total", "Events published to the bus", ["event_type", "service"]
)
EVENTS_CONSUMED = Counter(
    "mchpai_events_consumed_total", "Events consumed from the bus", ["event_type", "service"]
)
TOKENS_DISCOVERED = Counter(
    "mchpai_tokens_discovered_total", "New tokens discovered", ["source"]
)
BUY_SIGNALS = Counter("mchpai_buy_signals_total", "Buy signals generated", [])
TRADES_EXECUTED = Counter("mchpai_trades_executed_total", "Trades executed", ["mode"])

PREDICTION_LATENCY = Histogram(
    "mchpai_prediction_latency_ms", "Prediction compute latency (ms)",
    buckets=(1, 2, 5, 10, 25, 50, 100, 250, 500, 1000),
)
EXEC_LATENCY = Histogram(
    "mchpai_exec_latency_ms", "Decision→land latency (ms)",
    buckets=(5, 10, 25, 50, 100, 200, 400, 800, 1600),
)
FEATURE_COMPUTE_LATENCY = Histogram(
    "mchpai_feature_compute_latency_ms", "Feature computation latency (ms)",
    buckets=(1, 5, 10, 25, 50, 100, 250, 500),
)


def start_metrics_server(port: int = 9000) -> None:
    start_http_server(port)
