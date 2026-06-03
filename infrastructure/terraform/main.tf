# ===========================================================================
# MCHPAI — Terraform skeleton (production cloud footprint).
# This is intentionally provider-light scaffolding: fill in a concrete provider
# (AWS/GCP) per deployment. Modules map 1:1 to the data plane + compute plane.
# ===========================================================================

terraform {
  required_version = ">= 1.6"
  # backend "s3" { ... }   # remote state — configure per environment
}

variable "environment" {
  type    = string
  default = "production"
}

variable "region" {
  type    = string
  default = "us-east-1"
}

# --- Compute plane: Kubernetes cluster that runs the microservices ----------
module "kubernetes" {
  source      = "./modules/kubernetes"
  environment = var.environment
  # node pools: general (services), latency (execution-engine, colocated),
  # gpu (gnn/transformer training).
}

# --- Data plane -------------------------------------------------------------
module "postgres"   { source = "./modules/postgres"   environment = var.environment }
module "clickhouse" { source = "./modules/clickhouse" environment = var.environment }
module "neo4j"      { source = "./modules/neo4j"      environment = var.environment }
module "redis"      { source = "./modules/redis"      environment = var.environment }
module "nats"       { source = "./modules/nats"       environment = var.environment }
module "object_store" {
  source      = "./modules/object_store"   # MinIO/S3 for feature & model store
  environment = var.environment
}

# --- Observability ----------------------------------------------------------
module "observability" {
  source      = "./modules/observability"  # Prometheus, Grafana, Tempo, Loki
  environment = var.environment
}

output "summary" {
  value = "MCHPAI ${var.environment} skeleton — implement module bodies per cloud."
}
