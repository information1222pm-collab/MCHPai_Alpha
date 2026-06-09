#!/usr/bin/env python3
"""Collect REAL swaps from the public Solana RPC (no key) across DEX programs.

Standard JSON-RPC (getSignaturesForAddress + getTransaction jsonParsed) → the
canonical UniversalSwapParser → SQLite. A bounded, honest data-gather so the
backtester has a larger, broader real sample than the 92-min pump.fun-only set.

    python scripts/collect_public.py --seconds 240 --db data/public.db
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
import urllib.request
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "services", "firehose-ingestor"))
from firehose_ingestor.rpc import swaps_from_jsonparsed  # reuse the parser bridge

RPC = os.environ.get("PUBLIC_RPC", "https://api.mainnet-beta.solana.com")
PROGRAMS = {
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P": "pumpfun",
    "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA": "pumpswap",
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "raydium_amm",
    "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C": "raydium_cpmm",
}


PACE = float(os.environ.get("RPC_PACE", "0.12"))   # sleep between requests (be gentle on public RPC)


def rpc(method, params, tries=3):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    for a in range(tries):
        try:
            req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as r:
                j = json.load(r)
                time.sleep(PACE)
                if "result" in j:
                    return j["result"]
        except urllib.error.HTTPError as e:
            time.sleep(1.5 * (a + 1) if e.code == 429 else 0.5)   # back off hard on rate-limit
        except Exception:
            time.sleep(0.5 * (a + 1))
    return None


def db(path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    c = sqlite3.connect(path)
    c.execute("""CREATE TABLE IF NOT EXISTS swaps(
        signature TEXT, wallet TEXT, mint TEXT, side TEXT, sol_amount REAL,
        token_amount REAL, price REAL, dex TEXT, slot INTEGER, ts INTEGER,
        PRIMARY KEY(signature, wallet, mint, side))""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_mint ON swaps(mint, ts)")
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=240)
    ap.add_argument("--db", default="data/public.db")
    ap.add_argument("--sig-limit", type=int, default=25)
    args = ap.parse_args()

    conn = db(args.db)
    seen, stored, deadline = set(), 0, time.time() + args.seconds
    cycle = 0
    while time.time() < deadline:
        cycle += 1
        pend = []
        for pid in PROGRAMS:
            sigs = rpc("getSignaturesForAddress", [pid, {"limit": args.sig_limit}]) or []
            for s in sigs:
                sg = s.get("signature")
                if sg and not s.get("err") and sg not in seen:
                    pend.append(sg)
        for sg in pend[:60]:
            seen.add(sg)
            res = rpc("getTransaction", [sg, {"maxSupportedTransactionVersion": 0, "encoding": "jsonParsed"}])
            if not res:
                continue
            for sw in swaps_from_jsonparsed(res):
                try:
                    conn.execute("INSERT OR IGNORE INTO swaps VALUES(?,?,?,?,?,?,?,?,?,?)",
                                 (sw["signature"], sw["wallet"], sw["mint"], sw["side"],
                                  sw["sol"], sw["tok"], sw["price"], sw["dex"], 0, sw["ts"]))
                    stored += 1
                except Exception:
                    pass
        conn.commit()
        n = conn.execute("SELECT count(*) FROM swaps").fetchone()[0]
        nt = conn.execute("SELECT count(distinct mint) FROM swaps").fetchone()[0]
        print(f"cycle {cycle:>3} · {int(deadline-time.time()):>4}s left · stored~{stored} · "
              f"db rows {n} · tokens {nt}", flush=True)
        time.sleep(1.0)

    n, mn, mx = conn.execute("SELECT count(*), min(ts), max(ts) FROM swaps").fetchone()
    span = (mx - mn) if (mn and mx) else 0
    print(f"\nDONE · {n} swaps · {conn.execute('SELECT count(distinct mint) FROM swaps').fetchone()[0]} tokens "
          f"· span {span/60:.1f} min · db={args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
