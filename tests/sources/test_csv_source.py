"""CSVSource parses raw tabular observations into the exact same domain events,
deterministically."""

from __future__ import annotations

from pathlib import Path

from wis.domain.events import WalletBoughtToken, WalletCreated, WalletSoldToken
from wis.sources import CSVSource, collect

_CSV = """event,occurred_at,ingestion_time,wallet,token,base_raw,base_decimals,quote_raw,quote_decimals,funded_by,venue
created,1000,1001,alpha,,,,,,,
buy,2000,2001,alpha,GEM,1000000000,6,1000000000,9,,jup
sell,3000,3001,alpha,GEM,1000000000,6,3000000000,9,,jup
"""


def _write(tmp_path: Path) -> Path:
    path = tmp_path / "trades.csv"
    path.write_text(_CSV, encoding="utf-8")
    return path


def test_csv_parses_expected_events(tmp_path: Path) -> None:
    events = collect(CSVSource(_write(tmp_path)))
    kinds = [type(e.payload) for e in events]
    assert kinds == [WalletCreated, WalletBoughtToken, WalletSoldToken]

    buy = events[1].payload
    assert isinstance(buy, WalletBoughtToken)
    assert buy.base.raw == 1_000_000_000 and buy.base.decimals == 6
    assert buy.quote.raw == 1_000_000_000 and buy.quote.decimals == 9
    assert buy.venue == "jup"
    assert int(events[1].ingestion_time) == 2001


def test_csv_is_deterministic(tmp_path: Path) -> None:
    path = _write(tmp_path)
    a = [e.payload for e in collect(CSVSource(path))]
    b = [e.payload for e in collect(CSVSource(path))]
    assert a == b
