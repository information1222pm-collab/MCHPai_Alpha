"""ArchiveSource — the deterministic laboratory.

Most teams skip this. It is one of the most valuable things in the system.

An archive is a captured stream of domain events on disk (JSONL or Parquet).
Replaying it through the log reproduces ``wallet_state(t)`` *exactly*, every
time — which is what makes deterministic experiments, regression tests,
historical replay, paper trading and future simulation possible. Whatever a live
source observes today can be captured and replayed forever, identically.

The archive preserves ``ingestion_time`` per event, so point-in-time visibility
is reproduced faithfully — an experiment sees exactly what the system could have
seen, never more. The format is tolerant: it also reads archives that carry a
stored ``sequence`` / ``event_id`` (e.g. a MinIO replay dump); those are
re-appended and the log assigns fresh sequences, so an archive and a live feed
remain interchangeable inputs.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from pathlib import Path

from wis.domain.time import Nanos
from wis.eventsourcing.codec import decode_payload, encode_payload
from wis.eventsourcing.store import EventStore
from wis.sources.base import SourcedEvent


def encode_sourced(sourced: SourcedEvent) -> dict:
    return {"ingestion_time": int(sourced.ingestion_time), "payload": encode_payload(sourced.payload)}


def decode_sourced(record: dict) -> SourcedEvent:
    # Tolerant: works for both {ingestion_time,payload} and full stored-event
    # records that additionally carry sequence/event_id (which we ignore — the
    # log will assign its own).
    return SourcedEvent(
        payload=decode_payload(record["payload"]),
        ingestion_time=Nanos(int(record["ingestion_time"])),
    )


def capture(store: EventStore) -> list[SourcedEvent]:
    """Snapshot an existing log as a list of SourcedEvents (preserving ingestion
    time) so it can be written to an archive."""
    return [SourcedEvent(payload=e.payload, ingestion_time=e.ingestion_time) for e in store.read()]


def write_jsonl(events: Iterable[SourcedEvent], path: str | Path) -> int:
    n = 0
    with Path(path).open("w", encoding="utf-8") as fh:
        for sourced in events:
            fh.write(json.dumps(encode_sourced(sourced), sort_keys=True, separators=(",", ":")))
            fh.write("\n")
            n += 1
    return n


def write_parquet(events: Iterable[SourcedEvent], path: str | Path) -> int:
    import pyarrow as pa  # lazy
    import pyarrow.parquet as pq

    rows = list(events)
    table = pa.table(
        {
            "ingestion_time": [int(s.ingestion_time) for s in rows],
            "payload": [
                json.dumps(encode_payload(s.payload), sort_keys=True, separators=(",", ":")) for s in rows
            ],
        }
    )
    pq.write_table(table, str(path))
    return len(rows)


class ArchiveSource:
    """A :class:`~wis.sources.base.Source` backed by an on-disk event archive."""

    def __init__(self, path: str | Path, *, fmt: str = "auto", name: str | None = None) -> None:
        self._path = Path(path)
        self._fmt = self._resolve_fmt(fmt)
        self.name = name or f"archive:{self._path.name}"

    def _resolve_fmt(self, fmt: str) -> str:
        if fmt != "auto":
            return fmt
        suffix = self._path.suffix.lower()
        if suffix in (".parquet", ".pq"):
            return "parquet"
        return "jsonl"

    def event_stream(self) -> Iterator[SourcedEvent]:
        if self._fmt == "parquet":
            yield from self._read_parquet()
        else:
            yield from self._read_jsonl()

    def _read_jsonl(self) -> Iterator[SourcedEvent]:
        with self._path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield decode_sourced(json.loads(line))

    def _read_parquet(self) -> Iterator[SourcedEvent]:
        import pyarrow.parquet as pq  # lazy

        table = pq.read_table(str(self._path))
        ingestion = table.column("ingestion_time").to_pylist()
        payloads = table.column("payload").to_pylist()
        for ing, payload in zip(ingestion, payloads, strict=True):
            yield SourcedEvent(payload=decode_payload(json.loads(payload)), ingestion_time=Nanos(int(ing)))
