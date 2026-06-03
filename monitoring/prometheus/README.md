# Prometheus (monitoring)

The live scrape config used by docker-compose lives at
`infrastructure/prometheus/prometheus.yml`. Recording/alerting rules belong here
as the platform grows (SLOs on decision→land latency, signal throughput, etc.).
