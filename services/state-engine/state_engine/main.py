"""state-engine entrypoint."""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from datetime import datetime, timezone

from mchpai_common.config import settings
from mchpai_common.database import get_clickhouse, get_neo4j
from mchpai_common.events import Envelope, EventBus
from mchpai_common.events.subjects import TOKEN_CREATED, WALLET_BOUGHT, WALLET_SOLD
from mchpai_common.logging import configure as configure_logging, get_logger
from mchpai_common.schemas.common import Side
from mchpai_common.schemas.swap import Dex, SwapEvent
from mchpai_common.timelines import CreatorStateReducer, GraphStateReducer, WalletStateReducer

SERVICE = "state-engine"
MAX_REDUCERS = 200_000          # cap resident reducers (LRU eviction)
GRAPH_INTERVAL_SECONDS = 60

WALLET_COLS = ["ts", "address", "seq", "realized_pnl_sol", "unrealized_pnl_sol",
               "exposure_sol", "open_positions", "position_concentration",
               "conviction", "scaling", "cumulative_volume_sol", "trade_count"]
CREATOR_COLS = ["ts", "creator", "seq", "launches_so_far", "rugs_so_far", "rug_rate",
                "best_multiple_so_far", "alive_count", "cumulative_volume_sol"]
GRAPH_COLS = ["ts", "seq", "wallets", "co_buy_edges", "funded_edges", "transfer_edges",
              "clusters", "top_cluster_score", "density", "new_edges_delta"]


class LRU(OrderedDict):
    def __init__(self, cap: int) -> None:
        super().__init__()
        self.cap = cap

    def touch(self, key, factory):
        if key in self:
            self.move_to_end(key)
            return self[key]
        val = factory()
        self[key] = val
        if len(self) > self.cap:
            self.popitem(last=False)
        return val


async def main() -> None:
    configure_logging(level=settings.log_level, fmt=settings.log_format, service=SERVICE)
    log = get_logger(SERVICE)
    ch = get_clickhouse()
    bus = await EventBus(settings.nats_url, producer=SERVICE).connect()
    await bus.ensure_streams()

    wallets: LRU = LRU(MAX_REDUCERS)
    creators: LRU = LRU(MAX_REDUCERS)
    graph_reducer = GraphStateReducer()

    def w_row(s):
        return [s.ts, s.address, s.seq, s.realized_pnl_sol, s.unrealized_pnl_sol,
                s.exposure_sol, s.open_positions, s.position_concentration,
                s.conviction, s.scaling, s.cumulative_volume_sol, s.trade_count]

    async def on_swap(env: Envelope, side: Side) -> None:
        p = env.payload
        ts = datetime.fromisoformat(p["block_time"]) if p.get("block_time") else datetime.now(timezone.utc)
        reducer: WalletStateReducer = wallets.touch(p["wallet"], lambda: WalletStateReducer(p["wallet"]))
        state = reducer.apply(SwapEvent(
            signature=p.get("signature", ""), slot=p.get("slot") or 0, timestamp=ts,
            dex=Dex.unknown, wallet_address=p["wallet"], token_address=p["mint"], side=side,
            sol_amount=float(p.get("sol_amount", 0)), token_amount=float(p.get("token_amount", 0)),
            price=p.get("price_sol"),
        ))
        try:
            ch.insert("wallet_states", [w_row(state)], column_names=WALLET_COLS)
        except Exception as exc:  # noqa: BLE001
            log.warning("wallet_states.insert_failed", error=str(exc))

    async def on_token_created(env: Envelope) -> None:
        p = env.payload
        creator = p.get("creator")
        if not creator:
            return
        ts = datetime.fromisoformat(p["created_at"]) if p.get("created_at") else datetime.now(timezone.utc)
        reducer: CreatorStateReducer = creators.touch(creator, lambda: CreatorStateReducer(creator))
        s = reducer.on_launch(ts, volume_sol=float(p.get("initial_liquidity_sol") or 0))
        try:
            ch.insert("creator_states", [[s.ts, s.creator, s.seq, s.launches_so_far,
                       s.rugs_so_far, s.rug_rate, s.best_multiple_so_far, s.alive_count,
                       s.cumulative_volume_sol]], column_names=CREATOR_COLS)
        except Exception as exc:  # noqa: BLE001
            log.warning("creator_states.insert_failed", error=str(exc))

    async def graph_loop() -> None:
        driver = get_neo4j()
        while True:
            await asyncio.sleep(GRAPH_INTERVAL_SECONDS)
            try:
                async with driver.session() as sess:
                    res = await sess.run(
                        """
                        RETURN
                          count{ (w:Wallet) } AS wallets,
                          count{ ()-[:CO_BOUGHT]->() } AS co_buy,
                          count{ ()-[:FUNDED]->() } AS funded,
                          count{ ()-[:TRANSFERRED]->() } AS transfer,
                          count{ (c:Cluster) } AS clusters
                        """
                    )
                    rec = await res.single()
                gs = graph_reducer.snapshot(
                    datetime.now(timezone.utc),
                    wallets=int(rec["wallets"]), co_buy_edges=int(rec["co_buy"]),
                    funded_edges=int(rec["funded"]), transfer_edges=int(rec["transfer"]),
                    clusters=int(rec["clusters"]),
                )
                ch.insert("graph_states", [[gs.ts, gs.seq, gs.wallets, gs.co_buy_edges,
                          gs.funded_edges, gs.transfer_edges, gs.clusters,
                          gs.top_cluster_score, gs.density, gs.new_edges_delta]],
                          column_names=GRAPH_COLS)
                log.info("graph_state.recorded", seq=gs.seq, wallets=gs.wallets,
                         edges=gs.co_buy_edges + gs.funded_edges + gs.transfer_edges)
            except Exception as exc:  # noqa: BLE001
                log.warning("graph_state.failed", error=str(exc))

    await bus.subscribe(WALLET_BOUGHT, lambda e: on_swap(e, Side.buy), durable=f"{SERVICE}.bought")
    await bus.subscribe(WALLET_SOLD, lambda e: on_swap(e, Side.sell), durable=f"{SERVICE}.sold")
    await bus.subscribe(TOKEN_CREATED, on_token_created, durable=f"{SERVICE}.created")
    log.info("state-engine.started")
    await graph_loop()


if __name__ == "__main__":
    asyncio.run(main())
