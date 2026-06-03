# monitoring/

Observability stack provisioning. The OTel collector (`otel/config.yaml`) fans
telemetry to:

- **Prometheus** — metrics (scrape config in `infrastructure/prometheus/`)
- **Grafana** — dashboards (in `infrastructure/grafana/`)
- **Tempo** — distributed traces
- **Loki** — structured logs
- **Jaeger** — trace exploration (alt UI)

Every service emits OTLP to the collector via `OTEL_EXPORTER_OTLP_ENDPOINT`.
