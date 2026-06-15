"""Offline tests for the server-side firehose AlphaEngine + jsonParsed parser.

No network / web stack: drives the engine through MockFirehose and validates the
getTransaction(jsonParsed) -> swap parser on a hand-built fixture.
"""

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "services", "firehose-ingestor"))

from firehose_ingestor import AlphaEngine, MockFirehose, swaps_from_jsonparsed  # noqa: E402


# ----------------------------------------------------------------- jsonParsed parse
def _buy_tx():
    """Minimal jsonParsed getTransaction: TRADER spends 1 SOL, gains 1000 TOK on Raydium."""
    raydium = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
    start = 5_000_000_000
    fee = 5000
    return {
        "slot": 100,
        "blockTime": int(time.time()),
        "transaction": {
            "signatures": ["sigBUY"],
            "message": {
                "accountKeys": [{"pubkey": "TRADER"}, {"pubkey": "POOL"}, {"pubkey": raydium}],
                "instructions": [{"programId": raydium}],
            },
        },
        "meta": {
            "err": None,
            "fee": fee,
            "preBalances": [start, 0, 0],
            "postBalances": [start - 1_000_000_000 - fee, 0, 0],
            "preTokenBalances": [
                {"owner": "TRADER", "mint": "TOK", "uiTokenAmount": {"uiAmount": 0.0}}],
            "postTokenBalances": [
                {"owner": "TRADER", "mint": "TOK", "uiTokenAmount": {"uiAmount": 1000.0}}],
            "innerInstructions": [],
        },
    }


def test_jsonparsed_parses_buy():
    swaps = swaps_from_jsonparsed(_buy_tx())
    assert len(swaps) == 1
    s = swaps[0]
    assert s["wallet"] == "TRADER" and s["mint"] == "TOK" and s["side"] == "buy"
    assert abs(s["sol"] - 1.0) < 1e-6           # fee excluded from trade size
    assert abs(s["price"] - 0.001) < 1e-6       # 1 SOL / 1000 TOK


def test_jsonparsed_rejects_failed_tx():
    tx = _buy_tx()
    tx["meta"]["err"] = {"InstructionError": [0, "Custom"]}
    assert swaps_from_jsonparsed(tx) == []


# ------------------------------------------------------------------ engine via mock
def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_engine_aggregates_and_signals_via_mock_firehose():
    now = int(time.time())
    stream = []
    # 8 organic buyers, then a whale buy (>=5 SOL) -> whale signal
    for i in range(8):
        stream.append(dict(signature=f"s{i}", wallet=f"w{i}", mint="MINT",
                           side="buy", sol=0.8, tok=1000, price=0.001 * (1 + i * 0.05),
                           ts=now + i, dex="raydium_amm"))
    stream.append(dict(signature="whale", wallet="WHALE", mint="MINT", side="buy",
                       sol=8.0, tok=1000, price=0.0016, ts=now + 9, dex="raydium_amm"))

    engine = AlphaEngine()

    async def drive():
        async for sw in MockFirehose(stream).swaps():
            engine.ingest(sw)

    _run(drive())
    st = engine.stats()
    assert st["swaps"] == 9 and st["tokens"] == 1
    assert st["wallets"] == 9
    assert engine.counts.get("whale", 0) >= 1
    t = engine.tokens["MINT"]
    assert len(t.buyers) == 9 and t.buys == 9


def test_wallet_grading_rewards_winner_buyers():
    engine = AlphaEngine()
    now = int(time.time())
    # GW buys 4 tokens that each 3x by the grading horizon
    for r in range(4):
        m = f"win{r}"
        engine.ingest(dict(signature=f"g{r}", wallet="GW", mint=m, side="buy",
                           sol=1.0, tok=1000, price=0.001, ts=now - 200, dex="raydium_amm"))
        engine.tokens[m].last_price = 0.003   # 3x
    engine.grade_wallets(now)
    assert engine.wallet_q("GW") > 0.5         # proven positive forward-return

    # BW buys dumps -> negative grade
    for r in range(4):
        m = f"loss{r}"
        engine.ingest(dict(signature=f"b{r}", wallet="BW", mint=m, side="buy",
                           sol=1.0, tok=1000, price=0.001, ts=now - 200, dex="raydium_amm"))
        engine.tokens[m].last_price = 0.0004   # -60%
    engine.grade_wallets(now)
    assert engine.wallet_q("BW") < 0


def test_alpha_score_and_scan_emit():
    engine = AlphaEngine()
    now = int(time.time())
    # build a high-confluence token: many accelerating buyers, net buying
    for i in range(10):
        engine.ingest(dict(signature=f"a{i}", wallet=f"u{i}", mint="HOT", side="buy",
                           sol=1.0, tok=1000, price=0.001 * (1 + i * 0.05),
                           ts=now - 30 + i, dex="raydium_amm"))
    for i in range(8):
        engine.ingest(dict(signature=f"c{i}", wallet=f"v{i}", mint="HOT", side="buy",
                           sol=1.2, tok=1000, price=0.0016, ts=now - 8 + i, dex="raydium_amm"))
    a = engine.alpha_score("HOT", now)
    assert 0 <= a["score"] <= 100 and a["flow"] > 0
    engine.scan(now, alpha_min=20.0, trend_rate=4.0)
    types = {s["type"] for s in engine.top_signals(50)}
    assert "alpha" in types or "trend" in types
