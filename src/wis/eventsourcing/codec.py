"""The event codec — lossless, deterministic (de)serialization.

Every persistence adapter needs to turn a :class:`DomainEvent` into bytes and
back without losing or altering a single field. This codec is the shared,
authoritative translator, and it carries two non-negotiable properties:

* **Exact round trip.** ``decode(encode(e)) == e`` for every event. Cost basis,
  timestamps and identities must survive storage untouched — anything less and
  "same log → bit-identical state" is a lie.
* **Canonical bytes.** Encoding is deterministic (sorted keys, tight separators),
  so the same event always serializes to the same bytes on any machine. That is
  what lets a stored log be content-verified and compared across stores.

The codec is schema-evolution aware: it records ``event_type`` and
``event_version`` alongside the payload and dispatches decoding through the
:data:`EVENT_REGISTRY`. New event types are appended to the registry; old bytes
keep decoding forever.
"""

from __future__ import annotations

import json
import types
from dataclasses import fields
from typing import Any, Union, get_args, get_origin, get_type_hints

from wis.domain.events import EVENT_REGISTRY, DomainEvent
from wis.domain.identifiers import ClusterId, TokenMint, WalletAddress
from wis.domain.money import Amount
from wis.domain.time import Nanos, Sequence
from wis.eventsourcing.event import StoredEvent

# `Optional[X]` resolves to typing.Union; `X | None` (PEP 604) resolves to
# types.UnionType. Both must be recognised as unions.
_UNION_ORIGINS = (Union, types.UnionType)
_NoneType = type(None)
# Cache resolved field-type hints per event class (annotations are lazy strings
# under `from __future__ import annotations`).
_HINTS: dict[type, dict[str, Any]] = {}


def _hints(cls: type) -> dict[str, Any]:
    cached = _HINTS.get(cls)
    if cached is None:
        cached = get_type_hints(cls)
        _HINTS[cls] = cached
    return cached


# ---------------------------------------------------------------------------
# Value-level encode (driven by the concrete value) / decode (driven by the
# declared field type). Keeping decode annotation-driven is what lets us rebuild
# the exact typed objects — a bare string becomes a WalletAddress again.
# ---------------------------------------------------------------------------


def _encode_value(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, bool):  # before int — bool is an int subclass
        return v
    if isinstance(v, (WalletAddress, TokenMint, ClusterId)):
        return v.value
    if isinstance(v, Amount):
        return {"raw": v.raw, "decimals": v.decimals}
    if isinstance(v, (list, tuple)):
        return [_encode_value(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _encode_value(x) for k, x in v.items()}
    if isinstance(v, (int, float, str)):
        return v
    raise TypeError(f"cannot encode value of type {type(v)!r}")


def _unwrap_newtype(ann: Any) -> Any:
    return getattr(ann, "__supertype__", ann)


def _decode_value(ann: Any, raw: Any) -> Any:
    ann = _unwrap_newtype(ann)
    if raw is None:
        return None

    origin = get_origin(ann)
    if origin in _UNION_ORIGINS:  # Optional[X] / X | None
        non_none = [a for a in get_args(ann) if a is not _NoneType]
        return _decode_value(non_none[0], raw)
    if origin is tuple:
        (elem, *_rest) = get_args(ann)
        return tuple(_decode_value(elem, x) for x in raw)
    if origin is list:
        (elem,) = get_args(ann)
        return [_decode_value(elem, x) for x in raw]
    if origin is dict:
        return {str(k): v for k, v in raw.items()}

    if ann is WalletAddress:
        return WalletAddress(raw)
    if ann is TokenMint:
        return TokenMint(raw)
    if ann is ClusterId:
        return ClusterId(raw)
    if ann is Amount:
        return Amount(raw=int(raw["raw"]), decimals=int(raw["decimals"]))
    if ann is int:
        return int(raw)
    if ann is float:
        return float(raw)
    if ann is str:
        return raw
    if ann is bool:
        return bool(raw)
    # Literal[...] and anything else round-trips as the primitive it is.
    return raw


# ---------------------------------------------------------------------------
# Event / envelope (de)serialization
# ---------------------------------------------------------------------------


def encode_payload(event: DomainEvent) -> dict[str, Any]:
    body = {f.name: _encode_value(getattr(event, f.name)) for f in fields(event)}
    return {
        "type": event.EVENT_TYPE,
        "version": event.event_version,
        "body": body,
    }


def decode_payload(data: dict[str, Any]) -> DomainEvent:
    cls = EVENT_REGISTRY.get(data["type"])
    if cls is None:
        raise KeyError(f"unknown event type {data['type']!r}")
    hints = _hints(cls)
    body = data["body"]
    # Forward/backward compatible: a field absent from older serialized events
    # falls back to its dataclass default, so the schema can grow over decades
    # without breaking historical replay.
    kwargs = {}
    for f in fields(cls):
        if f.name in body:
            kwargs[f.name] = _decode_value(hints[f.name], body[f.name])
    return cls(**kwargs)  # type: ignore[return-value]


def encode_stored(stored: StoredEvent) -> dict[str, Any]:
    return {
        "sequence": int(stored.sequence),
        "ingestion_time": int(stored.ingestion_time),
        "event_id": stored.event_id,
        "payload": encode_payload(stored.payload),
    }


def decode_stored(data: dict[str, Any]) -> StoredEvent:
    return StoredEvent(
        sequence=Sequence(int(data["sequence"])),
        ingestion_time=Nanos(int(data["ingestion_time"])),
        event_id=data["event_id"],
        payload=decode_payload(data["payload"]),
    )


def dumps_payload(event: DomainEvent) -> str:
    """Canonical JSON string for a payload — deterministic bytes."""
    return json.dumps(encode_payload(event), sort_keys=True, separators=(",", ":"))


def loads_payload(text: str) -> DomainEvent:
    return decode_payload(json.loads(text))
