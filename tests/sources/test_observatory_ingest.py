"""The Observatory ingests any source through one door and immediately observes
the resulting wallet_state(t)."""

from __future__ import annotations

from pathlib import Path

from wis.app.observatory import Observatory
from wis.conformance import canonical_event_log
from wis.domain.identifiers import WalletAddress
from wis.sources import ArchiveSource, capture, write_jsonl


def test_ingest_source_feeds_the_log_and_state(tmp_path: Path) -> None:
    # Capture the canonical log to an archive, then ingest it through the facade.
    seed = Observatory()
    for payload, ingestion in canonical_event_log():
        seed.ingest(payload, ingestion_time=ingestion)
    path = tmp_path / "log.jsonl"
    write_jsonl(capture(seed.store), path)

    obs = Observatory()
    n = obs.ingest_source(ArchiveSource(path))
    assert n == len(canonical_event_log())

    report = obs.wallet_report(WalletAddress("alpha"))
    assert report is not None
    assert report.frame.sample_size >= 1
