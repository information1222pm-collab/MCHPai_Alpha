# Jaeger

Alternate trace-exploration UI. In dev, traces flow OTLP → otel-collector →
Tempo; Jaeger can be run with `OTEL` storage or as an all-in-one for local
debugging:

    docker run --rm -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one:latest
