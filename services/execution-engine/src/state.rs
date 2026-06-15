//! Shared state: Prometheus metrics + a tiny metrics HTTP server.

use std::convert::Infallible;
use std::sync::Arc;

use hyper::service::{make_service_fn, service_fn};
use hyper::{Body, Request, Response, Server};
use prometheus::{Encoder, Histogram, HistogramOpts, IntCounter, Registry, TextEncoder};
use tracing::info;

#[derive(Clone)]
pub struct Metrics {
    pub registry: Arc<Registry>,
    pub swaps_ingested: IntCounter,
    pub orders_consumed: IntCounter,
    pub trades_executed: IntCounter,
    pub exec_latency_ms: Histogram,
    pub parse_latency_us: Histogram,
}

impl Metrics {
    pub fn new() -> Self {
        let registry = Registry::new();
        let swaps_ingested =
            IntCounter::new("mchpai_swaps_ingested_total", "Swaps parsed from Geyser").unwrap();
        let orders_consumed =
            IntCounter::new("mchpai_orders_consumed_total", "Orders consumed").unwrap();
        let trades_executed =
            IntCounter::new("mchpai_trades_executed_total", "Trades executed").unwrap();
        let exec_latency_ms = Histogram::with_opts(
            HistogramOpts::new("mchpai_exec_latency_ms", "Decision→submit latency (ms)")
                .buckets(vec![1.0, 2.0, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0]),
        )
        .unwrap();
        let parse_latency_us = Histogram::with_opts(
            HistogramOpts::new("mchpai_parse_latency_us", "Swap parse latency (us)")
                .buckets(vec![50.0, 100.0, 250.0, 500.0, 1000.0, 5000.0, 15000.0]),
        )
        .unwrap();

        registry.register(Box::new(swaps_ingested.clone())).ok();
        registry.register(Box::new(orders_consumed.clone())).ok();
        registry.register(Box::new(trades_executed.clone())).ok();
        registry.register(Box::new(exec_latency_ms.clone())).ok();
        registry.register(Box::new(parse_latency_us.clone())).ok();

        Metrics {
            registry: Arc::new(registry),
            swaps_ingested,
            orders_consumed,
            trades_executed,
            exec_latency_ms,
            parse_latency_us,
        }
    }
}

pub async fn serve_metrics(port: u16, metrics: Metrics) {
    let make_svc = make_service_fn(move |_| {
        let metrics = metrics.clone();
        async move {
            Ok::<_, Infallible>(service_fn(move |_req: Request<Body>| {
                let metrics = metrics.clone();
                async move {
                    let mut buf = Vec::new();
                    let enc = TextEncoder::new();
                    enc.encode(&metrics.registry.gather(), &mut buf).ok();
                    Ok::<_, Infallible>(Response::new(Body::from(buf)))
                }
            }))
        }
    });

    let addr = ([0, 0, 0, 0], port).into();
    info!(%port, "metrics endpoint listening");
    if let Err(e) = Server::bind(&addr).serve(make_svc).await {
        tracing::error!(error = %e, "metrics server error");
    }
}
