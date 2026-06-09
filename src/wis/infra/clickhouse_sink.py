"""ClickHouse — the analytical fact table of closed trades.

ClickHouse is built for the billions-of-rows analytical scans the platform will
need. It is a derived store: each row is a closed trade from the projected world
(:func:`closed_trade_rows`). Money is stored as exact rational parts plus a float
approximation, so analytics are fast *and* reconciliation stays exact — the
exact total pnl read back must equal the oracle's.

The clickhouse-connect client is imported lazily.
"""

from __future__ import annotations

from fractions import Fraction

from wis.infra.projection_rows import TradeRow, closed_trade_rows
from wis.projections.wallet_projector import WalletWorld

_TABLE = "wis_closed_trades"

_COLUMNS = [
    "wallet", "token", "quote",
    "qty_num", "qty_den",
    "cost_num", "cost_den",
    "proceeds_num", "proceeds_den",
    "pnl_float",
    "entry_time", "exit_time",
    "entry_sequence", "exit_sequence",
]


class ClickHouseTradeSink:
    def __init__(self, host: str = "localhost", port: int = 8123, *, database: str = "default") -> None:
        import clickhouse_connect  # lazy

        self._client = clickhouse_connect.get_client(host=host, port=port, database=database)
        self._ensure_table()

    def _ensure_table(self) -> None:
        self._client.command(
            f"""
            CREATE TABLE IF NOT EXISTS {_TABLE} (
                wallet String, token String, quote String,
                qty_num Int64, qty_den Int64,
                cost_num Int64, cost_den Int64,
                proceeds_num Int64, proceeds_den Int64,
                pnl_float Float64,
                entry_time Int64, exit_time Int64,
                entry_sequence Int64, exit_sequence Int64
            ) ENGINE = MergeTree ORDER BY (exit_sequence, wallet, token)
            """
        )

    def insert_world(self, world: WalletWorld) -> int:
        rows = closed_trade_rows(world)
        if rows:
            data = [
                [
                    r.wallet, r.token, r.quote,
                    r.qty_num, r.qty_den,
                    r.cost_num, r.cost_den,
                    r.proceeds_num, r.proceeds_den,
                    r.pnl_float,
                    r.entry_time, r.exit_time,
                    r.entry_sequence, r.exit_sequence,
                ]
                for r in rows
            ]
            self._client.insert(_TABLE, data, column_names=_COLUMNS)
        return len(rows)

    def read_rows(self) -> list[TradeRow]:
        result = self._client.query(
            f"SELECT {', '.join(_COLUMNS)} FROM {_TABLE} ORDER BY exit_sequence, wallet, token"
        )
        return [TradeRow(*row) for row in result.result_rows]

    def exact_total_pnl(self) -> Fraction:
        total = Fraction(0)
        for r in self.read_rows():
            total += Fraction(r.proceeds_num, r.proceeds_den) - Fraction(r.cost_num, r.cost_den)
        return total

    def truncate(self) -> None:
        self._client.command(f"TRUNCATE TABLE IF EXISTS {_TABLE}")
