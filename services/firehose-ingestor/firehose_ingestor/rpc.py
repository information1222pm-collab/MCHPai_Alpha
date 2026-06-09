"""Helius JSON-RPC helpers + jsonParsed → SwapEvent bridge.

``ctx_from_jsonparsed`` turns a standard ``getTransaction`` (encoding=jsonParsed)
result into a :class:`TxContext` so the canonical ``UniversalSwapParser`` does the
balance-delta reconstruction — the same logic the dashboard runs, but server-side.
The builder is pure stdlib so it is unit-testable without a network or HTTP client.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from mchpai_common.parsing import TokenBalance, TxContext, parse_transaction

WSOL = "So11111111111111111111111111111111111111112"


def ctx_from_jsonparsed(res: dict) -> TxContext | None:
    """Build a TxContext from a getTransaction jsonParsed result."""
    meta = res.get("meta")
    tx = res.get("transaction") or {}
    msg = tx.get("message") or {}
    if not meta or meta.get("err") or not msg:
        return None
    keys = [k.get("pubkey") if isinstance(k, dict) else k for k in msg.get("accountKeys", [])]
    if not keys:
        return None
    fee_payer = keys[0]
    pre_bal = meta.get("preBalances") or []
    post_bal = meta.get("postBalances") or []
    pre_sol = {keys[i]: pre_bal[i] for i in range(min(len(keys), len(pre_bal)))}
    post_sol = {keys[i]: post_bal[i] for i in range(min(len(keys), len(post_bal)))}

    def _bal(entries):
        out = []
        for b in entries or []:
            owner = b.get("owner")
            mint = b.get("mint")
            ui = ((b.get("uiTokenAmount") or {}).get("uiAmount")) or 0.0
            if owner and mint:
                out.append(TokenBalance(owner=owner, mint=mint, amount=float(ui)))
        return out

    pids = set()
    for ix in msg.get("instructions", []) or []:
        if ix.get("programId"):
            pids.add(ix["programId"])
    for inr in meta.get("innerInstructions", []) or []:
        for ix in inr.get("instructions", []) or []:
            if ix.get("programId"):
                pids.add(ix["programId"])

    return TxContext(
        signature=res.get("transaction", {}).get("signatures", [""])[0] if isinstance(res.get("transaction"), dict) else "",
        slot=res.get("slot", 0),
        timestamp=datetime.fromtimestamp(res.get("blockTime") or 0, tz=timezone.utc),
        fee_payer=fee_payer,
        program_ids=list(pids),
        pre_sol_lamports=pre_sol,
        post_sol_lamports=post_sol,
        pre_token_balances=_bal(meta.get("preTokenBalances")),
        post_token_balances=_bal(meta.get("postTokenBalances")),
        fee_lamports=meta.get("fee", 0),
    )


def swaps_from_jsonparsed(res: dict) -> list[dict]:
    """Parse a jsonParsed tx into normalized swap dicts the engine consumes."""
    ctx = ctx_from_jsonparsed(res)
    if ctx is None:
        return []
    ts = int(ctx.timestamp.timestamp())
    out = []
    for ev in parse_transaction(ctx):
        out.append(dict(
            signature=ev.signature, wallet=ev.wallet_address, mint=ev.token_address,
            side=ev.side.value, sol=ev.sol_amount, tok=ev.token_amount,
            price=ev.price or 0.0, ts=ts, dex=ev.dex.value,
        ))
    return out


class HeliusRpc:
    """Minimal async JSON-RPC client (lazy aiohttp import so import stays light)."""

    def __init__(self, api_key: str):
        self.url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
        self._session = None

    async def _sess(self):
        if self._session is None:
            import aiohttp  # lazy: only needed when actually fetching
            self._session = aiohttp.ClientSession()
        return self._session

    async def call(self, method: str, params: list):
        sess = await self._sess()
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        for attempt in range(3):
            try:
                async with sess.post(self.url, json=body, timeout=20) as r:
                    j = await r.json()
                    if "error" in j:
                        return None
                    return j.get("result")
            except Exception:
                await asyncio.sleep(0.4 * (attempt + 1))
        return None

    async def get_transaction(self, sig: str):
        return await self.call("getTransaction", [sig, {"maxSupportedTransactionVersion": 0, "encoding": "jsonParsed"}])

    async def close(self):
        if self._session is not None:
            await self._session.close()
            self._session = None
