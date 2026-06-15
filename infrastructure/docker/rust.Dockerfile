# Multi-stage build for the Rust execution-engine (lowest-latency path).
FROM rust:1.79-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
      pkg-config libssl-dev protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

COPY services/execution-engine/Cargo.toml services/execution-engine/Cargo.lock* ./
# Pre-build deps with a stub main for caching.
RUN mkdir src && echo "fn main() {}" > src/main.rs && cargo build --release || true
COPY services/execution-engine/src ./src
RUN cargo build --release

FROM debian:bookworm-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates libssl3 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /build/target/release/execution-engine /usr/local/bin/execution-engine
EXPOSE 9100
ENTRYPOINT ["/usr/local/bin/execution-engine"]
