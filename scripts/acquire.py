#!/usr/bin/env python3
"""MCHPAI data-acquisition runner (bootstrap / sandbox).

Polls Helius (Enhanced Transactions API) for launchpad activity, runs every
transaction through the *real* ``UniversalSwapParser`` (balance-delta), and
persists reality to a local SQLite store:

    token_births   — sacred, idempotent (a birth recorded once, never overwritten)
    swaps          — the firehose of real swaps
    snapshots      — derived deterministically from stored swaps (ordered)

This is the bootstrap acquisition path. In a full deployment the same events flow
through Yellowstone → NATS → Postgres/ClickHouse; here we accumulate real data
without the heavy stack so acquisition can *begin now*. It reuses library code
only — no new intelligence.

Usage:
    HELIUS_API_KEY=... python scripts/acquire.py --minutes 15
    HELIUS_API_KEY=... python scripts/acquire.py --build-snapshots
    python scripts/acquire.py --stats
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime, timezone

from mchpai_common.parsing import TokenBalance, TxContext, parse_transaction
from mchpai_common.parsing.program_ids import detect_dex
from mchpai_common.schemas.common import Side
from mchpai_common.schemas.swap import Dex, SwapEvent
from mchpai_common.snapshots import MultiWindowAggregator

DB_PATH = os.environ.get("ACQUIRE_DB", "data/acquisition.db")
API_KEY = os.environ.get("HELIUS_API_KEY", "")
ENH = "https://api-mainnet.helius-rpc.com/v0/addresses/{addr}/transactions/"

# Launchpads to observe (program id -> label)
PROGRAMS = {
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P": "pumpfun",
    "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA": "pumpswap",
}
RATE_SLEEP = 0.25  # be polite to the API / protect credits


# --------------------------------------------------------------------- storage
def db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS token_births(
            mint TEXT PRIMARY KEY, birth_slot INTEGER, birth_timestamp INTEGER,
            creator TEXT, launchpad TEXT, first_signature TEXT, recorded_at INTEGER);
        CREATE TABLE IF NOT EXISTS swaps(
            signature TEXT, wallet TEXT, mint TEXT, side TEXT,
            sol_amount REAL, token_amount REAL, price REAL, dex TEXT,
            slot INTEGER, ts INTEGER,
            PRIMARY KEY(signature, wallet, mint, side));
        CREATE INDEX IF NOT EXISTS idx_swaps_mint ON swaps(mint, ts);
        CREATE TABLE IF NOT EXISTS snapshots(
            mint TEXT, window TEXT, seq INTEGER, ts INTEGER, age_seconds REAL,
            phase TEXT, price_sol REAL, volume_sol REAL, buyers INTEGER,
            sellers INTEGER, txns INTEGER, net_flow_sol REAL, entropy REAL,
            PRIMARY KEY(mint, window, seq));
        """
    )
    return conn


# ------------------------------------------------------------------ http + parse
def fetch(addr: str, before: str | None, ttype: str | None, limit: int = 100) -> list[dict]:
    url = ENH.format(addr=addr) + f"?api-key={API_KEY}&limit={limit}"
    if before:
        url += f"&before={before}"
    if ttype:
        url += f"&type={ttype}"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return []


def ctx_from_enhanced(tx: dict) -> TxContext:
    pre_sol, post_sol, post_tok = {}, {}, []
    for ad in tx.get("accountData", []):
        acct = ad["account"]
        pre_sol[acct] = 0
        post_sol[acct] = ad.get("nativeBalanceChange", 0)  # delta-encoded
        for tbc in ad.get("tokenBalanceChanges") or []:
            rta = tbc.get("rawTokenAmount") or {}
            try:
                amt = int(rta.get("tokenAmount", "0")) / (10 ** int(rta.get("decimals", 0)))
            except Exception:
                amt = 0.0
            post_tok.append(TokenBalance(owner=tbc.get("userAccount", ""), mint=tbc["mint"], amount=amt))
    pids = set()
    for ix in tx.get("instructions", []):
        if ix.get("programId"):
            pids.add(ix["programId"])
        for inner in ix.get("innerInstructions", []) or []:
            if inner.get("programId"):
                pids.add(inner["programId"])
    return TxContext(
        signature=tx.get("signature", ""), slot=tx.get("slot", 0),
        timestamp=datetime.fromtimestamp(tx.get("timestamp", 0), tz=timezone.utc),
        fee_payer=tx.get("feePayer", ""), program_ids=list(pids),
        pre_sol_lamports=pre_sol, post_sol_lamports=post_sol,
        pre_token_balances=[], post_token_balances=post_tok,
        fee_lamports=tx.get("fee", 0),
    )


def record_birth(conn, tx: dict, launchpad: str) -> bool:
    mint = None
    for ad in tx.get("accountData", []):
        for tbc in ad.get("tokenBalanceChanges") or []:
            if tbc.get("mint", "").endswith("pump") or tbc.get("mint"):
                mint = tbc["mint"]
                break
        if mint:
            break
    if not mint:
        for tt in tx.get("tokenTransfers", []):
            if tt.get("mint"):
                mint = tt["mint"]
                break
    if not mint:
        return False
    cur = conn.execute(
        "INSERT OR IGNORE INTO token_births VALUES (?,?,?,?,?,?,?)",
        (mint, tx.get("slot"), tx.get("timestamp"), tx.get("feePayer"),
         launchpad, tx.get("signature"), int(time.time())),
    )
    return cur.rowcount > 0


def record_swaps(conn, tx: dict) -> int:
    try:
        events = parse_transaction(ctx_from_enhanced(tx))
    except Exception:
        return 0
    n = 0
    for e in events:
        cur = conn.execute(
            "INSERT OR IGNORE INTO swaps VALUES (?,?,?,?,?,?,?,?,?,?)",
            (e.signature, e.wallet_address, e.token_address, e.side.value,
             e.sol_amount, e.token_amount, e.price, e.dex.value, e.slot,
             int(e.timestamp.timestamp())),
        )
        n += cur.rowcount
    return n


# ---------------------------------------------------------------------- commands
def stats(conn) -> dict:
    births = conn.execute("SELECT count(*) FROM token_births").fetchone()[0]
    swaps = conn.execute("SELECT count(*) FROM swaps").fetchone()[0]
    snaps = conn.execute("SELECT count(*) FROM snapshots").fetchone()[0]
    tokens = conn.execute(
        "SELECT count(*) FROM (SELECT mint FROM token_births UNION SELECT mint FROM swaps)"
    ).fetchone()[0]
    return {"births": births, "tokens": tokens, "swaps": swaps, "snapshots": snaps,
            "milestones": {"snapshots_1M": snaps / 1_000_000, "tokens_10k": tokens / 10_000,
                           "tokens_100k": tokens / 100_000}}


def run_acquire(minutes: float) -> None:
    if not API_KEY:
        print("HELIUS_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    conn = db()
    deadline = time.time() + minutes * 60
    cursors = {pid: {"create": None, "all": None} for pid in PROGRAMS}
    cycle = 0
    while time.time() < deadline:
        cycle += 1
        new_b = new_s = 0
        for pid, label in PROGRAMS.items():
            # births stream (CREATE)
            page = fetch(pid, cursors[pid]["create"], "CREATE", 100)
            time.sleep(RATE_SLEEP)
            if page:
                cursors[pid]["create"] = page[-1]["signature"]
                for tx in page:
                    new_b += record_birth(conn, tx, label)
            # swaps stream (all types; SWAP processed)
            page = fetch(pid, cursors[pid]["all"], None, 100)
            time.sleep(RATE_SLEEP)
            if page:
                cursors[pid]["all"] = page[-1]["signature"]
                for tx in page:
                    if tx.get("type") == "CREATE":
                        new_b += record_birth(conn, tx, label)
                    new_s += record_swaps(conn, tx)
        conn.commit()
        s = stats(conn)
        print(f"[cycle {cycle:>4}] +{new_b} births +{new_s} swaps | "
              f"births={s['births']} tokens={s['tokens']} swaps={s['swaps']}", flush=True)
        if new_b == 0 and new_s == 0:
            time.sleep(2)
    build_snapshots(conn)
    print("ACQUIRE_DONE", json.dumps(stats(conn)), flush=True)


def build_snapshots(conn) -> None:
    """Deterministically derive snapshots from stored swaps (ordered by ts)."""
    conn.execute("DELETE FROM snapshots")
    mints = [r[0] for r in conn.execute(
        "SELECT mint FROM swaps GROUP BY mint HAVING count(*) >= 3").fetchall()]
    total = 0
    for mint in mints:
        rows = conn.execute(
            "SELECT signature, wallet, side, sol_amount, token_amount, price, slot, ts "
            "FROM swaps WHERE mint=? ORDER BY ts, slot", (mint,)).fetchall()
        if not rows:
            continue
        birth_ts = datetime.fromtimestamp(rows[0][7], tz=timezone.utc)
        agg = MultiWindowAggregator(mint, birth_ts)
        for sig, wallet, side, sol, tok, price, slot, ts in rows:
            ev = SwapEvent(signature=sig, slot=slot or 0,
                           timestamp=datetime.fromtimestamp(ts, tz=timezone.utc),
                           dex=Dex.unknown, wallet_address=wallet, token_address=mint,
                           side=Side(side), sol_amount=sol, token_amount=tok, price=price)
            for window, snaps in agg.add(ev).items():
                for sn in snaps:
                    conn.execute(
                        "INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (mint, sn.window.value, sn.seq, int(sn.ts.timestamp()), sn.age_seconds,
                         None, sn.price_sol, sn.volume_sol, sn.buyers, sn.sellers, sn.txns,
                         sn.net_flow_sol, sn.entropy))
                    total += 1
        for window, snaps in agg.flush().items():
            for sn in snaps:
                conn.execute(
                    "INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (mint, sn.window.value, sn.seq, int(sn.ts.timestamp()), sn.age_seconds,
                     None, sn.price_sol, sn.volume_sol, sn.buyers, sn.sellers, sn.txns,
                     sn.net_flow_sol, sn.entropy))
                total += 1
    conn.commit()
    print(f"snapshots built: {total} from {len(mints)} mints", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=15)
    ap.add_argument("--build-snapshots", action="store_true")
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()

    if args.stats:
        print(json.dumps(stats(db()), indent=2))
        return 0
    if args.build_snapshots:
        build_snapshots(db())
        print(json.dumps(stats(db()), indent=2))
        return 0
    run_acquire(args.minutes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
