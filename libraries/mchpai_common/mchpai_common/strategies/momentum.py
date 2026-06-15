"""Momentum + buy/sell-ratio trading strategy (the canonical, testable logic).

The same rules run in three places — the dashboard paper-bot (JS port), the
``scripts/trader.py`` runner (paper + gated live), and the unit tests — so behavior
is identical everywhere.

Signals
-------
* **buy/sell ratio** = buy_volume / sell_volume over the token's activity. > ratio_in
  means buyers dominate (pressure up).
* **momentum** = price change over the last ``mom_window`` observations.

Entry (BUY) when ratio and momentum are both strong and structural filters pass.
Exit (SELL) on take-profit, stop-loss, trailing stop, momentum reversal, sell
pressure, or max hold. This is a fast, mean-exit momentum scalper — appropriate
for memecoins, and *expected to be marginal-to-negative* without real edge, which
is exactly why it ships paper-first.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StrategyParams:
    size_sol: float = 0.5          # base stake (used when liq_fraction == 0)
    max_positions: int = 5
    take_profit: float = 0.40      # fixed TP (ignored when runner=True)
    stop_loss: float = -0.20       # -20%
    trail: float = 0.25            # give back this fraction from peak -> exit
    ratio_in: float = 2.0          # buy_vol >= 2x sell_vol to enter
    ratio_out: float = 0.7         # ratio collapses -> exit
    mom_in: float = 0.05           # +5% momentum to enter
    mom_out: float = -0.02         # momentum turns down -> exit
    mom_window: int = 5
    hold_max_s: int = 600
    min_buyers: int = 3
    min_vol_sol: float = 1.0       # buy+sell volume floor
    min_age_s: int = 8             # avoid the first chaotic seconds
    max_age_s: int = 900
    fee: float = 0.02              # simple-book round-trip cost (dashboard parity)
    smart_min: int = 0             # require >= N experienced wallets early (0=off)

    # --- "wiser" levers (improvements) ---
    liq_fraction: float = 0.0      # >0: size = clamp(liq_fraction*liquidity, min/max ticket)
    min_ticket: float = 0.1
    max_ticket: float = 1.0
    min_liquidity_sol: float = 0.0 # skip tokens with thin liquidity (avoid garbage + slippage)
    runner: bool = False           # True: no fixed TP — let winners run on a trailing stop
    exit_reversal: bool = True     # exit on momentum reversal (noisy; can disable)
    exit_pressure: bool = True     # exit on sell-pressure (noisy; can disable)


def position_size(p: StrategyParams, liquidity: float) -> float:
    """Liquidity-aware sizing — never shove a fixed ticket into a thin pool."""
    if p.liq_fraction <= 0:
        return p.size_sol
    return max(p.min_ticket, min(p.max_ticket, p.liq_fraction * liquidity))


@dataclass
class Features:
    price: float
    buy_vol: float
    sell_vol: float
    buyers: int
    age_s: float
    prices: list[float] = field(default_factory=list)
    smart_buyers: int = 0          # experienced wallets (seen before this token) buying early
    liquidity: float = 0.0         # liquidity proxy (SOL) for sizing + quality filter

    def ratio(self) -> float:
        return self.buy_vol / (self.sell_vol + 1e-9)

    def momentum(self, window: int) -> float:
        p = self.prices
        if len(p) < 2:
            return 0.0
        ref = p[max(0, len(p) - 1 - window)]
        return (p[-1] / ref - 1.0) if ref > 0 else 0.0


@dataclass
class Position:
    mint: str
    entry: float
    size_sol: float
    tokens: float
    opened_ts: float
    peak: float = 0.0


def entry_signal(f: Features, p: StrategyParams) -> bool:
    return (
        f.ratio() >= p.ratio_in
        and f.momentum(p.mom_window) >= p.mom_in
        and f.buyers >= p.min_buyers
        and (f.buy_vol + f.sell_vol) >= p.min_vol_sol
        and f.liquidity >= p.min_liquidity_sol  # quality: avoid thin/garbage pools
        and p.min_age_s <= f.age_s <= p.max_age_s
        and f.smart_buyers >= p.smart_min       # unique edge: ride experienced money
        and f.price > 0
    )


def exit_signal(pos: Position, f: Features, p: StrategyParams, hold_s: float | None = None) -> tuple[bool, str]:
    if f.price <= 0:
        return (False, "")
    ret = f.price / pos.entry - 1.0
    # hard stop always protects capital
    if ret <= p.stop_loss:
        return (True, "stop_loss")
    # trailing stop lets winners run, then locks gains
    if pos.peak > 0 and f.price <= pos.peak * (1 - p.trail):
        return (True, "trailing_stop")
    # fixed take-profit only when NOT in runner mode (runner = ride the fat tail)
    if not p.runner and ret >= p.take_profit:
        return (True, "take_profit")
    # optional (noisy) exits — disable to stop churning on wiggles
    if p.exit_reversal and f.momentum(p.mom_window) <= p.mom_out:
        return (True, "momentum_reversal")
    if p.exit_pressure and f.ratio() < p.ratio_out:
        return (True, "sell_pressure")
    hold = hold_s if hold_s is not None else f.age_s
    if hold >= p.hold_max_s:
        return (True, "timeout")
    return (False, "")


class PaperBook:
    """Deterministic paper portfolio — simulates fills at the observed price."""

    def __init__(self, params: StrategyParams, start_sol: float = 10.0) -> None:
        self.p = params
        self.cash = start_sol
        self.start = start_sol
        self.positions: dict[str, Position] = {}
        self.closed: list[dict] = []
        self.realized = 0.0

    def on_tick(self, mint: str, f: Features, ts: float) -> list[dict]:
        events: list[dict] = []
        pos = self.positions.get(mint)
        if pos:
            pos.peak = max(pos.peak, f.price)
            do, reason = exit_signal(pos, f, self.p, hold_s=ts - pos.opened_ts)
            if do:
                proceeds = pos.tokens * f.price * (1 - self.p.fee)
                pnl = proceeds - pos.size_sol
                self.cash += proceeds
                self.realized += pnl
                self.closed.append({"mint": mint, "pnl": pnl,
                                    "ret": f.price / pos.entry - 1.0, "reason": reason, "ts": ts})
                del self.positions[mint]
                events.append({"action": "sell", "mint": mint, "price": f.price, "pnl": pnl, "reason": reason})
        elif len(self.positions) < self.p.max_positions and self.cash >= self.p.size_sol:
            if entry_signal(f, self.p):
                cost = self.p.size_sol * (1 + self.p.fee)
                if self.cash >= cost:
                    self.cash -= cost
                    self.positions[mint] = Position(mint, f.price, self.p.size_sol,
                                                    self.p.size_sol / f.price, ts, f.price)
                    events.append({"action": "buy", "mint": mint, "price": f.price})
        return events

    def equity(self, marks: dict[str, float]) -> float:
        open_val = sum(pos.tokens * marks.get(m, pos.entry) for m, pos in self.positions.items())
        return self.cash + open_val

    def stats(self) -> dict:
        wins = sum(1 for c in self.closed if c["pnl"] > 0)
        n = len(self.closed)
        return {"realized": self.realized, "trades": n, "open": len(self.positions),
                "win_rate": (wins / n) if n else 0.0, "cash": self.cash}
