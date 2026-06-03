"""Structured, JSON-first logging for every service.

One ``configure()`` call wires structlog to emit machine-parseable JSON (or
pretty console in dev), with consistent keys so logs from 100+ services collate
cleanly in Loki. ``get_logger(name)`` returns a bound logger.
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure(*, level: str = "INFO", fmt: str = "json", service: str = "mchpai") -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=getattr(logging, level.upper(), 20))

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    processors.append(
        structlog.processors.JSONRenderer()
        if fmt == "json"
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper(), 20)),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    structlog.contextvars.bind_contextvars(service=service)


def get_logger(name: str = "mchpai"):
    return structlog.get_logger(name)
