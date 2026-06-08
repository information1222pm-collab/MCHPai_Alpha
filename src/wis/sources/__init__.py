"""Sources — the reality interface. One door for the world.

Every source turns observations into the same domain events and feeds them to
the single source of truth (the event log). Sources are interchangeable: the
historical :class:`ArchiveSource` laboratory and a live Helius/Yellowstone/RPC
feed produce identical behavior downstream.

    Source → Domain Events → Event Log → Replay → wallet_state(t)

The archive is the deterministic laboratory (replay, regression, paper trading,
simulation). Live sources are reality; capture them into an archive to make them
replayable. Sources never build wallet state directly — they only fill the log.
"""

from __future__ import annotations

from wis.sources.archive_source import ArchiveSource, capture, write_jsonl
from wis.sources.base import Source, SourcedEvent, collect, pump
from wis.sources.csv_source import CSVSource
from wis.sources.helius_source import HeliusSource, translate_helius
from wis.sources.rpc_source import RPCSource, translate_rpc
from wis.sources.synthetic_source import SyntheticConfig, SyntheticSource
from wis.sources.yellowstone_source import YellowstoneSource, translate_yellowstone

__all__ = [
    "Source",
    "SourcedEvent",
    "pump",
    "collect",
    "ArchiveSource",
    "capture",
    "write_jsonl",
    "CSVSource",
    "SyntheticSource",
    "SyntheticConfig",
    "HeliusSource",
    "translate_helius",
    "YellowstoneSource",
    "translate_yellowstone",
    "RPCSource",
    "translate_rpc",
]
