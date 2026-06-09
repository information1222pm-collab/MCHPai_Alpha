"""Server-side Alpha engine — full-firehose port of the dashboard's brain.

This is the *same* intelligence that runs in ``observation.html`` (wallet-quality
grading, the composite Alpha Score, and the multi-detector signal feed), but fed
by the **complete** DEX firehose instead of a browser poll sample. Pure Python —
stdlib only — so it is unit-testable offline without any network or web stack.

Feed it normalized swap dicts via :meth:`AlphaEngine.ingest`::

    {signature, wallet, mint, side('buy'|'sell'), sol, tok, price, ts(int), dex}

and read :meth:`top_signals` / :meth:`top_alpha` for what is firing right now.
"""

from __future__ import annotations

import math
import statistics
from collections import deque
from dataclasses import dataclass, field

# --- price sanitization (data purity) — mirrors the dashboard ---
MIN_SOL_PX = 0.005   # dust below this gives an unreliable price
MAX_DEV = 5.0        # reject a price deviating >5x from the token's rolling median
GRADE_HORIZON = 150  # seconds before a wallet's pick is scored on forward return
WHALE_SOL = 5.0      # single buy size that trips the whale detector
SIG_DEDUPE = 60      # per (type, mint) signal cooldown seconds


@dataclass
class TokenState:
    birth: int
    last_seen: int = 0
    first_price: float = 0.0
    last_price: float = 0.0
    max_mult: float = 1.0
    buys: int = 0
    sells: int = 0
    vol: float = 0.0
    net_sol: float = 0.0
    buyers: set = field(default_factory=set)
    smart: set = field(default_factory=set)
    follow: set = field(default_factory=set)
    follow_sell_ts: int = 0
    prices: list = field(default_factory=list)
    med: deque = field(default_factory=lambda: deque(maxlen=12))
    bsamp: list = field(default_factory=list)   # [(ts, buyers, vol)] for accel / liq-growth

    def clean_price(self, price: float, sol: float) -> bool:
        if not price or price <= 0 or sol < MIN_SOL_PX:
            return False
        if len(self.med) >= 3:
            m = statistics.median(self.med)
            if m > 0 and (price / m > MAX_DEV or price / m < 1.0 / MAX_DEV):
                return False
        return True


class AlphaEngine:
    def __init__(self, follows: set[str] | None = None):
        self.tokens: dict[str, TokenState] = {}
        self.wallet_first: dict[str, int] = {}
        self.wallet_alpha: dict[str, list] = {}   # addr -> [ema, n]
        self.grade_q: deque = deque(maxlen=20000)
        self.follows: set[str] = set(follows or [])
        self.signals: deque = deque(maxlen=400)
        self.sig_seen: dict[str, int] = {}
        self.counts: dict[str, int] = {}
        self.swaps_seen = 0
        self.now = 0

    # ---------------------------------------------------------------- grading
    def wallet_q(self, addr: str) -> float:
        wa = self.wallet_alpha.get(addr)
        return wa[0] if wa and wa[1] >= 2 else 0.0

    def grade_wallets(self, now: int) -> None:
        """Resolve picks older than the horizon into a per-wallet forward-return EMA."""
        while self.grade_q and now - self.grade_q[0][3] >= GRADE_HORIZON:
            wallet, mint, entry, _ts = self.grade_q.popleft()
            t = self.tokens.get(mint)
            if t and entry > 0 and t.last_price > 0:
                fwd = max(-1.0, min(20.0, t.last_price / entry - 1.0))
                wa = self.wallet_alpha.setdefault(wallet, [0.0, 0])
                wa[0] += (fwd - wa[0]) / min(wa[1] + 1, 30)
                wa[1] += 1
        if len(self.wallet_alpha) > 40000:
            for k in [k for k, v in self.wallet_alpha.items() if v[1] < 3]:
                self.wallet_alpha.pop(k, None)

    # ------------------------------------------------------------------ score
    def _feat(self, t: TokenState, now: int) -> dict:
        bv = (t.vol + t.net_sol) / 2
        sv = (t.vol - t.net_sol) / 2
        p = t.prices
        mom = (p[-1] / p[max(0, len(p) - 6)] - 1) if len(p) >= 2 else 0.0
        return dict(price=t.last_price, ratio=bv / (sv + 1e-9), mom=mom,
                    buyers=len(t.buyers), smart=len(t.smart), age=now - t.birth,
                    vol=bv + sv, liq=t.vol, bv=bv, sv=sv)

    def alpha_score(self, mint: str, now: int) -> dict:
        t = self.tokens.get(mint)
        if not t:
            return dict(score=0.0)
        f = self._feat(t, now)
        smart_w = sum(min(2.0, self.wallet_q(a)) for a in t.buyers if self.wallet_q(a) > 0)
        follow = len(t.follow)
        accel = liq_g = 0.0
        s = t.bsamp
        if len(s) >= 4:
            h = len(s) // 2
            e, m, l = s[0], s[h], s[-1]
            r1 = (m[1] - e[1]) / max(m[0] - e[0], 1)
            r2 = (l[1] - m[1]) / max(l[0] - m[0], 1)
            accel = r2 - r1
            liq_g = (l[2] - m[2]) / max(m[2], 1)
        netflow = (f["bv"] - f["sv"]) / (f["bv"] + f["sv"] + 1e-9)
        organic = min(1.0, len(t.buyers) / max(t.buys, 1))
        recency = 1.0 if now - t.last_seen < 90 else 0.0
        c_smart = min(1.0, (smart_w + follow * 1.5) / 4)
        c_accel = max(0.0, min(1.0, accel * 60 / 8))
        c_flow = max(0.0, min(1.0, netflow))
        c_liq = max(0.0, min(1.0, liq_g * 4))
        c_org = organic
        c_mom = max(0.0, min(1.0, f["mom"] * 5))
        score = 100 * (0.30 * c_smart + 0.20 * c_accel + 0.18 * c_flow +
                       0.12 * c_liq + 0.10 * c_org + 0.10 * c_mom) * recency
        return dict(score=score, smart=c_smart, accel=c_accel, flow=c_flow,
                    liq=c_liq, org=c_org, mom=c_mom)

    # ---------------------------------------------------------------- signals
    def _sig(self, typ: str, mint: str, now: int, **extra) -> None:
        k = f"{typ}|{mint}"
        if self.sig_seen.get(k) and now - self.sig_seen[k] < SIG_DEDUPE:
            return
        self.sig_seen[k] = now
        if len(self.sig_seen) > 8000:
            self.sig_seen.clear()
        self.signals.appendleft(dict(type=typ, mint=mint, ts=now, **extra))
        self.counts[typ] = self.counts.get(typ, 0) + 1

    # ----------------------------------------------------------------- ingest
    def ingest(self, sw: dict) -> None:
        mint = sw["mint"]
        wallet = sw["wallet"]
        side = sw["side"]
        sol = float(sw.get("sol") or 0)
        price = float(sw.get("price") or 0)
        ts = int(sw.get("ts") or self.now)
        self.now = max(self.now, ts)
        self.swaps_seen += 1
        self.wallet_first.setdefault(wallet, ts)
        t = self.tokens.get(mint)
        if t is None:
            t = self.tokens[mint] = TokenState(birth=ts)
        t.last_seen = ts

        if t.clean_price(price, sol):
            if not t.first_price:
                t.first_price = price
            t.last_price = price
            t.prices.append(price)
            if len(t.prices) > 30:
                t.prices.pop(0)
            t.med.append(price)
            if t.first_price:
                t.max_mult = max(t.max_mult, price / t.first_price)

        t.vol += sol
        if side == "buy":
            t.buys += 1
            t.buyers.add(wallet)
            if self.wallet_first.get(wallet, ts) < t.birth:
                t.smart.add(wallet)
            t.net_sol += sol
        else:
            t.sells += 1
            t.net_sol -= sol

        if sw.get("follow") or wallet in self.follows:
            if side == "buy":
                t.follow.add(wallet)
            else:
                t.follow_sell_ts = ts

        # time-series sample (accel / liquidity-growth)
        if not t.bsamp or ts - t.bsamp[-1][0] >= 4:
            t.bsamp.append((ts, len(t.buyers), t.vol))
            if len(t.bsamp) > 16:
                t.bsamp.pop(0)
        if side == "buy" and price > 0:
            self.grade_q.append((wallet, mint, price, ts))

        # detectors
        if side == "buy":
            if sol >= WHALE_SOL:
                self._sig("whale", mint, ts, sol=round(sol, 2))
            q = self.wallet_q(wallet)
            if q > 0.3:
                self._sig("smart", mint, ts, q=round(q, 2))
            if wallet in self.follows:
                self._sig("copy", mint, ts)
        bs = t.bsamp
        if len(bs) >= 4:
            lv, mv = bs[-1], bs[len(bs) // 2]
            if lv[2] > mv[2] * 3 and lv[2] - mv[2] > 3:
                self._sig("volsurge", mint, ts)
        if (t.first_price and t.last_price >= t.first_price * 2 and ts - t.birth > 30
                and side == "buy" and price >= t.last_price):
            self._sig("breakout", mint, ts, x=round(t.last_price / t.first_price, 1))

    # ------------------------------------------------------------- periodic scan
    def scan(self, now: int, alpha_min: float = 68.0, trend_rate: float = 8.0) -> None:
        """Emit alpha-fire and trending signals across active tokens (call ~7s)."""
        self.grade_wallets(now)
        for mint, t in self.tokens.items():
            if now - t.last_seen >= 90 or len(t.buyers) < 4 or t.last_price <= 0:
                continue
            a = self.alpha_score(mint, now)
            if a["score"] >= alpha_min:
                self._sig("alpha", mint, now, score=int(a["score"]))
            age = now - t.birth
            if age > 0 and len(t.buyers) / age * 60 >= trend_rate:
                self._sig("trend", mint, now)

    # ------------------------------------------------------------- maintenance
    def maintain(self, now: int, max_tokens: int = 20000, max_wallets: int = 300000,
                 stale: int = 1800) -> None:
        """Bound memory for a 24/7 server: drop stale/oldest tokens + wallet_first."""
        if len(self.tokens) > max_tokens:
            ordered = sorted(self.tokens.items(), key=lambda kv: kv[1].last_seen)
            for mint, _t in ordered[: len(self.tokens) - max_tokens]:
                self.tokens.pop(mint, None)
        elif len(self.tokens) > max_tokens // 2:
            for mint in [m for m, t in self.tokens.items() if now - t.last_seen > stale]:
                self.tokens.pop(mint, None)
        if len(self.wallet_first) > max_wallets:
            ordered = sorted(self.wallet_first.items(), key=lambda kv: kv[1])
            for addr, _ts in ordered[: len(self.wallet_first) - max_wallets]:
                self.wallet_first.pop(addr, None)
        if len(self.sig_seen) > 8000:
            self.sig_seen.clear()

    # ----------------------------------------------------------------- readers
    def top_signals(self, n: int = 40) -> list[dict]:
        return list(self.signals)[:n]

    def top_alpha(self, n: int = 12, min_score: float = 40.0) -> list[dict]:
        now = self.now
        out = []
        for mint, t in self.tokens.items():
            if now - t.last_seen >= 90 or len(t.buyers) < 4 or t.last_price <= 0:
                continue
            a = self.alpha_score(mint, now)
            if a["score"] >= min_score:
                out.append(dict(mint=mint, max_mult=round(t.max_mult, 2),
                                buyers=len(t.buyers), **{k: round(v, 3) for k, v in a.items()}))
        out.sort(key=lambda x: -x["score"])
        return out[:n]

    def stats(self) -> dict:
        graded = sum(1 for v in self.wallet_alpha.values() if v[1] >= 2)
        proven = sum(1 for v in self.wallet_alpha.values() if v[1] >= 2 and v[0] > 0)
        return dict(swaps=self.swaps_seen, tokens=len(self.tokens),
                    wallets=len(self.wallet_first), graded=graded, proven=proven,
                    signals=len(self.signals), counts=dict(self.counts))
