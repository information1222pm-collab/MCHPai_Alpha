"""The universal event envelope.

Every message on the bus is an :class:`Envelope`. The envelope carries routing
and observability metadata (id, type, schema version, timestamp, trace id,
producer) plus an opaque ``payload`` dict that deserializes to a typed event.
This lets infrastructure (logging, tracing, replay, dead-lettering) be fully
generic while business code stays strongly typed.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from ..schemas.common import SCHEMA_VERSION


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Envelope(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str                              # EventType value
    schema_version: str = SCHEMA_VERSION
    occurred_at: datetime = Field(default_factory=_now)
    producer: str = "unknown"              # service name
    trace_id: str | None = None            # propagated for distributed tracing
    partition_key: str | None = None       # e.g. mint/wallet for ordered replay
    payload: dict = Field(default_factory=dict)

    @classmethod
    def wrap(
        cls,
        event_type: str,
        payload: BaseModel | dict,
        *,
        producer: str = "unknown",
        trace_id: str | None = None,
        partition_key: str | None = None,
    ) -> "Envelope":
        body = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else dict(payload)
        return cls(
            type=event_type,
            producer=producer,
            trace_id=trace_id,
            partition_key=partition_key,
            payload=body,
        )
