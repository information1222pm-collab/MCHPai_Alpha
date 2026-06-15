#!/usr/bin/env python3
"""MCHPAI trader — momentum + buy/sell-ratio bot.

Three modes, paper-first by hard default:

  --backtest   replay the acquired swaps (data/acquisition.db) through the
               strategy and report PnL vs always-hold. No network, no risk.
  --paper      poll live mainnet and PAPER-trade (simulated fills) — watch it
               buy/sell in real time with full PnL. Default. No real orders.
  --live       REAL execution via Jupiter. DISABLED unless you pass
               --i-understand-the-risk AND set EXECUTION_MODE=live AND provide a
               funded WALLET_KEYPAIR_PATH. Honors per-trade size, max positions,
               and a daily loss limit kill-switch.

Honesty: a buy/sell-ratio + momentum bot on memecoins gets front-run, sandwiched,
and rugged; expect losses. Validate in --backtest and --paper first. The code is
correct; the edge is unproven. Live trading risks real funds — your decision.

    python scripts/trader.py --backtest
    HELIUS_API_KEY=… python scripts/trader.py --paper
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scripts.acquire as acq  # reuse fetch + parser (Enhanced API, server-side)
from mchpai_common.strategies import Features, PaperBook, StrategyParams

ACQ_DB = os.environ.get("ACQUIRE_DB", "data/acquisition.db")
TRADE_DB = os.environ.get("TRADE_DB", "data/trades.db")
DAILY_LOSS_LIMIT = float(os.environ.get("DAILY_LOSS_LIMIT_SOL", "3.0"))

WSOL = "So11111111111111111111111111111111111111112"


class TokenState:
    __slots__ = ("first_ts", "last_ts", "first_price", "last_price",
                 "buy_vol", "sell_vol", "buyers", "prices")

    def __init__(self, ts):
        self.first_ts = self.last_ts = ts
        self.first_price = self.last_price = 0.0
        self.buy_vol = self.sell_vol = 0.0
        self.buyers = set()
        self.prices = []

    def update(self, side, sol, price, wallet, ts):
        self.last_ts = ts
        if price:
            if not self.first_price:
                self.first_price = price
            self.last_price = price
            self.prices.append(price)
            if len(self.prices) > 30:
                self.prices.pop(0)
        if side == "buy":
            self.buy_vol += sol
            self.buyers.add(wallet)
        else:
            self.sell_vol += sol

    def features(self, ts):
        return Features(price=self.last_price, buy_vol=self.buy_vol, sell_vol=self.sell_vol,
                        buyers=len(self.buyers), age_s=ts - self.first_ts, prices=list(self.prices))


def trade_db():
    os.makedirs(os.path.dirname(TRADE_DB) or ".", exist_ok=True)
    c = sqlite3.connect(TRADE_DB, timeout=10)
    c.execute("CREATE TABLE IF NOT EXISTS trades(ts INTEGER, mode TEXT, mint TEXT, action TEXT, "
              "price REAL, size_sol REAL, pnl REAL, reason TEXT)")
    return c


def log_trade(db, mode, ev, size):
    db.execute("INSERT INTO trades VALUES (?,?,?,?,?,?,?,?)",
               (int(time.time()), mode, ev["mint"], ev["action"], ev.get("price"),
                size, ev.get("pnl"), ev.get("reason", "")))
    db.commit()


# --------------------------------------------------------------- backtest (realistic)
def backtest(params: StrategyParams) -> None:
    """Realistic single-config backtest (delegates to the research engine, which
    applies latency, slippage/impact, fees, and failures). For a parameter search
    use: python scripts/research.py"""
    import scripts.research as R
    from mchpai_common.strategies import CostModel
    rows, wfirst, ticks = R.load()
    if not rows:
        print("no swaps in acquisition.db — run scripts/acquire.py first")
        return
    m = R.backtest(rows, wfirst, ticks, params, CostModel())
    print("=== REALISTIC BACKTEST (smart-money momentum, full costs) ===")
    print(f"swaps replayed : {len(rows)}")
    print(f"trades         : {m['trades']:.0f}   win-rate: {m['win_rate']*100:.0f}%")
    print(f"net PnL        : {m['net_pnl']:+.3f} SOL   ({m['ret_pct']:+.1f}%)")
    print(f"profit factor  : {min(m['profit_factor'],9.99):.2f}   sharpe: {m['sharpe']:.2f}   "
          f"max DD: {m['max_dd_pct']:.1f}%")
    print(f"avg slippage   : {m['avg_slip_bps']:.0f} bps")
    print("Run `python scripts/research.py` to search parameters honestly.")


# --------------------------------------------------------------- live execution (gated)
class LiveExecutor:
    def __init__(self):
        self.enabled = False
        self.keypair = None
        self.pubkey = None

    def arm(self):
        """Only arms if fully + explicitly configured. Otherwise stays off."""
        if os.environ.get("EXECUTION_MODE") != "live":
            return False
        path = os.environ.get("WALLET_KEYPAIR_PATH", "")
        if not path or not os.path.exists(path):
            print("LIVE refused: WALLET_KEYPAIR_PATH not set / missing.")
            return False
        try:
            import json
            from solders.keypair import Keypair  # lazy: pip install solders solana
            self.keypair = Keypair.from_bytes(bytes(json.load(open(path))))
            self.pubkey = str(self.keypair.pubkey())
            self.enabled = True
            print(f"LIVE armed for wallet {self.pubkey[:8]}…  (real funds at risk)")
            return True
        except Exception as e:  # noqa: BLE001
            print(f"LIVE refused: {e}")
            return False

    def execute(self, side, mint, size_sol):
        """Real swap via Jupiter. Outline kept explicit; requires solders+solana."""
        if not self.enabled:
            return None
        import base64
        import httpx
        from solders.transaction import VersionedTransaction
        rpc = os.environ.get("SOLANA_RPC_URLS", os.environ.get("HELIUS_RPC_URL", ""))
        in_mint, out_mint = (WSOL, mint) if side == "buy" else (mint, WSOL)
        lamports = int(size_sol * 1e9)
        with httpx.Client(timeout=20) as c:
            q = c.get("https://quote-api.jup.ag/v6/quote", params={
                "inputMint": in_mint, "outputMint": out_mint, "amount": lamports,
                "slippageBps": 300}).json()
            swap = c.post("https://quote-api.jup.ag/v6/swap", json={
                "quoteResponse": q, "userPublicKey": self.pubkey,
                "wrapAndUnwrapSol": True, "dynamicComputeUnitLimit": True,
                "prioritizationFeeLamports": "auto"}).json()
            raw = base64.b64decode(swap["swapTransaction"])
            tx = VersionedTransaction.from_bytes(raw)
            signed = VersionedTransaction(tx.message, [self.keypair])
            sig = c.post(rpc, json={"jsonrpc": "2.0", "id": 1, "method": "sendTransaction",
                "params": [base64.b64encode(bytes(signed)).decode(),
                           {"encoding": "base64", "skipPreflight": True}]}).json()
        return sig.get("result")


# --------------------------------------------------------------- paper / live loop
def run_live(params: StrategyParams, live: bool) -> None:
    if not acq.API_KEY:
        print("HELIUS_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    mode = "live" if live else "paper"
    executor = LiveExecutor()
    if live and not executor.arm():
        print("Falling back to PAPER (live not armed).")
        mode = "paper"

    book = PaperBook(params, start_sol=params.size_sol * 20)
    states: dict[str, TokenState] = {}
    cursors = {pid: None for pid in acq.PROGRAMS}
    db = trade_db()
    paused = False
    print(f"=== TRADER [{mode.upper()}] === size={params.size_sol}◎ max_pos={params.max_positions} "
          f"TP=+{params.take_profit*100:.0f}% SL={params.stop_loss*100:.0f}%")

    while True:
        marks = {}
        for pid in acq.PROGRAMS:
            page = acq.fetch(pid, cursors[pid], None, 100)
            if page:
                cursors[pid] = page[-1]["signature"]
                for tx in page:
                    try:
                        for ev in acq.parse_transaction(acq.ctx_from_enhanced(tx)):
                            st = states.get(ev.token_address) or states.setdefault(
                                ev.token_address, TokenState(int(ev.timestamp.timestamp())))
                            ts = int(ev.timestamp.timestamp())
                            st.update(ev.side.value, ev.sol_amount, ev.price or 0,
                                      ev.wallet_address, ts)
                            marks[ev.token_address] = ev.price or st.last_price
                            if paused:
                                continue
                            for tev in book.on_tick(ev.token_address, st.features(ts), ts):
                                log_trade(db, mode, tev, params.size_sol)
                                tag = "BUY " if tev["action"] == "buy" else "SELL"
                                extra = (f" pnl={tev['pnl']:+.3f} ({tev['reason']})"
                                         if tev["action"] == "sell" else "")
                                print(f"  {tag} {ev.token_address[:10]} @ {tev['price']:.2e}{extra}")
                                if mode == "live":
                                    sig = executor.execute(tev["action"], ev.token_address, params.size_sol)
                                    if sig:
                                        print(f"       submitted {sig[:16]}…")
                    except Exception:
                        pass
            time.sleep(0.25)
        s = book.stats()
        eq = book.equity(marks)
        if s["realized"] <= -DAILY_LOSS_LIMIT and not paused:
            paused = True
            print(f"  !! DAILY LOSS LIMIT hit ({s['realized']:+.2f}◎) — trading PAUSED")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] equity={eq:.3f}◎ "
              f"({(eq/book.start-1)*100:+.1f}%) realized={s['realized']:+.3f}◎ "
              f"open={s['open']} trades={s['trades']} win={s['win_rate']*100:.0f}%"
              + ("  [PAUSED]" if paused else ""))
        time.sleep(2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backtest", action="store_true")
    ap.add_argument("--paper", action="store_true")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--i-understand-the-risk", action="store_true")
    ap.add_argument("--size", type=float, default=0.5)
    ap.add_argument("--max-positions", type=int, default=5)
    args = ap.parse_args()
    params = StrategyParams(size_sol=args.size, max_positions=args.max_positions)

    if args.backtest:
        backtest(params)
        return 0
    if args.live:
        if not args.i_understand_the_risk:
            print("LIVE blocked. Re-run with --i-understand-the-risk and set "
                  "EXECUTION_MODE=live + WALLET_KEYPAIR_PATH. (You can lose all funds.)")
            return 2
        run_live(params, live=True)
        return 0
    run_live(params, live=False)  # default: paper
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
