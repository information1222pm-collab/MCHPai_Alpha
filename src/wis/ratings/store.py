"""The rating store — where ratings live, designed to scale.

A :class:`RatingStore` protocol with a durable :class:`SqliteRatingStore`
reference (and an in-memory one for tests). The schema is deliberately flat and
columnar-friendly so the same upserts map onto PostgreSQL or ClickHouse at
100k–millions of wallets: only the adapter changes, not the rating pipeline.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Protocol, runtime_checkable

from wis.ratings.model import WalletRating

_SCHEMA = """
CREATE TABLE IF NOT EXISTS wallet_ratings (
    wallet          TEXT PRIMARY KEY,
    closed_trades   INTEGER NOT NULL,
    distinct_tokens INTEGER NOT NULL,
    open_positions  INTEGER NOT NULL,
    confidence      REAL NOT NULL,
    win_rate        REAL,
    median_multiple REAL,
    average_multiple REAL,
    sharpe          REAL,
    alpha_score     REAL,
    ev_score        REAL,
    conviction_score REAL,
    risk_score      REAL,
    timing_score    REAL,
    primary_quote   TEXT,
    primary_pnl     REAL,
    primary_roi     REAL,
    pnl_by_quote    TEXT,
    roi_by_quote    TEXT
);
CREATE INDEX IF NOT EXISTS ratings_alpha ON wallet_ratings (alpha_score);
CREATE INDEX IF NOT EXISTS ratings_winrate ON wallet_ratings (win_rate);
"""

_COLS = (
    "wallet", "closed_trades", "distinct_tokens", "open_positions", "confidence",
    "win_rate", "median_multiple", "average_multiple", "sharpe",
    "alpha_score", "ev_score", "conviction_score", "risk_score", "timing_score",
    "primary_quote", "primary_pnl", "primary_roi", "pnl_by_quote", "roi_by_quote",
)


def _row(r: WalletRating) -> tuple:
    return (
        r.wallet, r.closed_trades, r.distinct_tokens, r.open_positions, r.confidence,
        r.win_rate, r.median_multiple, r.average_multiple, r.sharpe,
        r.alpha_score, r.expected_value_score, r.conviction_score, r.risk_score, r.timing_score,
        r.primary_quote, r.primary_pnl, r.primary_roi,
        json.dumps(r.pnl_by_quote, sort_keys=True), json.dumps(r.roi_by_quote, sort_keys=True),
    )


@runtime_checkable
class RatingStore(Protocol):
    def upsert(self, ratings: Iterable[WalletRating]) -> int: ...
    def get(self, wallet: str) -> WalletRating | None: ...
    def top(self, by: str = "alpha_score", *, min_trades: int = 0,
            min_confidence: float = 0.0, limit: int = 50) -> list[WalletRating]: ...
    def count(self) -> int: ...


class SqliteRatingStore:
    """Durable rating store. Same shape a Postgres/ClickHouse adapter implements."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.executescript(_SCHEMA)

    def upsert(self, ratings: Iterable[WalletRating]) -> int:
        placeholders = ",".join("?" * len(_COLS))
        rows = [_row(r) for r in ratings]
        self._conn.executemany(
            f"INSERT OR REPLACE INTO wallet_ratings ({','.join(_COLS)}) VALUES ({placeholders})", rows
        )
        self._conn.commit()
        return len(rows)

    def get(self, wallet: str) -> WalletRating | None:
        cur = self._conn.execute(
            f"SELECT {','.join(_COLS)} FROM wallet_ratings WHERE wallet = ?", (wallet,)
        )
        row = cur.fetchone()
        return _to_rating(row) if row else None

    def top(self, by: str = "alpha_score", *, min_trades: int = 0,
            min_confidence: float = 0.0, limit: int = 50) -> list[WalletRating]:
        if by not in _COLS:
            raise ValueError(f"cannot rank by unknown column {by!r}")
        sql = (
            f"SELECT {','.join(_COLS)} FROM wallet_ratings "
            f"WHERE closed_trades >= ? AND confidence >= ? AND {by} IS NOT NULL "
            f"ORDER BY {by} DESC LIMIT ?"
        )
        return [_to_rating(r) for r in self._conn.execute(sql, (min_trades, min_confidence, limit))]

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM wallet_ratings").fetchone()[0])

    def __iter__(self) -> Iterator[WalletRating]:
        for row in self._conn.execute(f"SELECT {','.join(_COLS)} FROM wallet_ratings"):
            yield _to_rating(row)


def _to_rating(row: tuple) -> WalletRating:
    d = dict(zip(_COLS, row, strict=True))
    return WalletRating(
        wallet=d["wallet"],
        closed_trades=d["closed_trades"],
        distinct_tokens=d["distinct_tokens"],
        open_positions=d["open_positions"],
        confidence=d["confidence"],
        win_rate=d["win_rate"],
        median_multiple=d["median_multiple"],
        average_multiple=d["average_multiple"],
        sharpe=d["sharpe"],
        alpha_score=d["alpha_score"],
        expected_value_score=d["ev_score"],
        conviction_score=d["conviction_score"],
        risk_score=d["risk_score"],
        timing_score=d["timing_score"],
        primary_quote=d["primary_quote"],
        pnl_by_quote=json.loads(d["pnl_by_quote"]) if d["pnl_by_quote"] else {},
        roi_by_quote=json.loads(d["roi_by_quote"]) if d["roi_by_quote"] else {},
    )
