# deployments/

Per-environment deployment overlays (Kustomize/Helm values + env-specific config).

- `local/`      — docker-compose driven dev (see root `docker-compose.yml`)
- `staging/`    — pre-prod K8s overlay; live providers, paper execution
- `production/` — production K8s overlay; live execution, HA stores

Base manifests live in `infrastructure/kubernetes/`; overlays patch replica
counts, resources, node affinity (e.g. execution-engine → latency pool), and
secrets references.
