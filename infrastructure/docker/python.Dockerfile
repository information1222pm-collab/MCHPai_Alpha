# Shared base image for all Python microservices.
# Build arg SERVICE selects which service package to install on top of the
# shared mchpai_common library. Keeps a single, cached dependency layer.
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (build tools for native wheels, libpq for psycopg).
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# 1) Shared library first (changes least often → best layer caching).
COPY libraries/mchpai_common /app/libraries/mchpai_common
RUN pip install -e /app/libraries/mchpai_common

# 2) The selected service.
ARG SERVICE
COPY services/${SERVICE} /app/services/${SERVICE}
RUN pip install -e /app/services/${SERVICE}

# Default Prometheus metrics port.
EXPOSE 9000
