"""CSVSource — raw tabular observations into domain events.

A pragmatic ingestion path for trade dumps and backfills. The parser is a pure
function of the row, so a CSV replays deterministically just like an archive.
Amounts are taken as on-chain raw integers plus decimals wherever possible
(lossless); a human-float column is accepted as a fallback.

Canonical columns (only those relevant to a row's ``event`` are required):

* ``event`` — one of ``created | funded | price | buy | sell``
* ``occurred_at`` — event time in integer nanoseconds
* ``ingestion_time`` — optional; defaults to ``occurred_at``
* trade: ``wallet, token, base_raw, base_decimals, quote_raw, quote_decimals``
* funded: ``source, target, amount_raw, amount_decimals``
* price: ``token, price_raw, price_decimals``
* optional: ``funded_by, venue``
"""

from __future__ import annotations

import csv
from collections.abc import Iterator, Mapping
from pathlib import Path

from wis.domain.time import Nanos
from wis.sources import build
from wis.sources.base import SourcedEvent


def _int(row: Mapping[str, str], key: str) -> int:
    return int(row[key])


def parse_row(row: Mapping[str, str]) -> SourcedEvent:
    """Pure: one CSV row → one SourcedEvent. Raises on malformed rows rather
    than guessing — reality should be ingested faithfully or rejected loudly."""
    event = row["event"].strip().lower()
    at = _int(row, "occurred_at")
    ingestion = Nanos(int(row["ingestion_time"]) if row.get("ingestion_time") else at)

    if event == "created":
        payload = build.created(row["wallet"], at, funded_by=row.get("funded_by") or None)
    elif event == "funded":
        amount = build.amount_from_raw(_int(row, "amount_raw"), _int(row, "amount_decimals"))
        payload = build.funding(row["source"], row["target"], amount, at)
    elif event == "price":
        p = build.amount_from_raw(_int(row, "price_raw"), _int(row, "price_decimals"))
        payload = build.price(row["token"], p, at)
    elif event in ("buy", "sell"):
        base = build.amount_from_raw(_int(row, "base_raw"), _int(row, "base_decimals"))
        quote = build.amount_from_raw(_int(row, "quote_raw"), _int(row, "quote_decimals"))
        venue = row.get("venue") or None
        fn = build.buy if event == "buy" else build.sell
        payload = fn(row["wallet"], row["token"], base, quote, at, venue=venue)
    else:
        raise ValueError(f"unknown event kind {event!r}")

    return SourcedEvent(payload=payload, ingestion_time=ingestion)


class CSVSource:
    def __init__(self, path: str | Path, *, name: str | None = None) -> None:
        self._path = Path(path)
        self.name = name or f"csv:{self._path.name}"

    def event_stream(self) -> Iterator[SourcedEvent]:
        with self._path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                yield parse_row(row)
