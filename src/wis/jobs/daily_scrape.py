"""Daily wallet scrape — find active, strong-performing trading wallets.

Discover candidate wallets, observe each through the existing Helius pipeline,
rate them, and keep those that are **active** (≥ N closed trades and ≥ N
trades/day) with **strong** performance (truth-weighted alpha above a floor and a
positive primary-quote ROI). Writes a dated CSV + a small summary; optionally
upserts to a RatingStore.

Honesty built in:
* "5,000/day with ≥5 trades/day and strong metrics" is a **high bar**. In
  observed data only a small fraction of fee payers clear it, so the job scrapes
  within a candidate/time budget and emits *those that qualify* — it reports the
  shortfall rather than padding the list. A target is a goal, not a guarantee.
* Every emitted wallet carries its denominators (closed trades, confidence).
* PnL is per quote asset; alpha is confidence-shrunk (it distrusts flash).
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass, field

from wis.eventsourcing.replay import ReplayEngine
from wis.eventsourcing.store import InMemoryEventStore
from wis.projections.wallet_projector import WalletProjector
from wis.ratings.model import WalletRating
from wis.ratings.rater import rate_wallet
from wis.sources.helius_source import HeliusSource

# High-activity DEX/program addresses to discover trading wallets from.
DEFAULT_PROGRAMS = (
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4",   # Jupiter v6
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",   # Raydium AMM v4
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",   # pump.fun
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",   # Orca Whirlpools
    "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo",   # Meteora DLMM
)


@dataclass(frozen=True, slots=True)
class ScrapeConfig:
    target: int = 5000                 # desired qualifying wallets
    candidate_budget: int = 60000      # max wallets to observe (rate/credit cap)
    pages_per_wallet: int = 2          # depth of each wallet's history
    # "Active" criteria:
    min_trades: int = 5
    min_trades_per_day: float = 5.0
    # "Strong performance" criteria:
    min_alpha: float = 0.55
    min_confidence: float = 0.20
    require_positive_roi: bool = True
    time_budget_seconds: float = 18000.0  # 5h (GitHub Actions job cap is 6h)


@dataclass(slots=True)
class ScrapeResult:
    qualifying: list[WalletRating] = field(default_factory=list)
    candidates_observed: int = 0
    candidates_discovered: int = 0
    elapsed_seconds: float = 0.0
    stopped_reason: str = ""

    @property
    def met_target(self) -> bool:
        return len(self.qualifying) >= 1 and self.stopped_reason == "target_reached"


def is_active(r: WalletRating, cfg: ScrapeConfig) -> bool:
    return r.closed_trades >= cfg.min_trades and r.trades_per_day >= cfg.min_trades_per_day


def is_strong(r: WalletRating, cfg: ScrapeConfig) -> bool:
    if r.confidence < cfg.min_confidence:
        return False
    if r.alpha_score is None or r.alpha_score < cfg.min_alpha:
        return False
    return not (cfg.require_positive_roi and not (r.primary_roi is not None and r.primary_roi > 0))


def qualifies(r: WalletRating, cfg: ScrapeConfig) -> bool:
    """Pure filter: an active trading wallet with strong performance."""
    return is_active(r, cfg) and is_strong(r, cfg)


def rate_one(transport, wallet: str, cfg: ScrapeConfig) -> WalletRating | None:
    """Observe one wallet and rate it. Returns None on observation failure."""
    try:
        txs = transport.transactions(wallet, limit=100, max_pages=cfg.pages_per_wallet)
    except Exception:
        return None
    if not txs:
        return None
    store = InMemoryEventStore()
    for sourced in HeliusSource(txs).event_stream():
        store.append(sourced.payload, ingestion_time=sourced.ingestion_time)
    world = ReplayEngine(store, WalletProjector()).run()
    from wis.domain.identifiers import WalletAddress

    ws = world.wallets.get(WalletAddress(wallet))
    return rate_wallet(ws, prices=world.prices) if ws is not None else None


def scrape(transport, candidates: Iterator[str], cfg: ScrapeConfig) -> ScrapeResult:
    """Drive the scrape over a candidate stream within budgets."""
    result = ScrapeResult()
    start = time.monotonic()
    seen: set[str] = set()
    for wallet in candidates:
        if wallet in seen:
            continue
        seen.add(wallet)
        result.candidates_discovered += 1

        if len(result.qualifying) >= cfg.target:
            result.stopped_reason = "target_reached"
            break
        if result.candidates_observed >= cfg.candidate_budget:
            result.stopped_reason = "candidate_budget_exhausted"
            break
        if time.monotonic() - start >= cfg.time_budget_seconds:
            result.stopped_reason = "time_budget_exhausted"
            break

        r = rate_one(transport, wallet, cfg)
        result.candidates_observed += 1
        if r is not None and qualifies(r, cfg):
            result.qualifying.append(r)

    if not result.stopped_reason:
        result.stopped_reason = "candidates_exhausted"
    result.elapsed_seconds = time.monotonic() - start
    # Best wallets first.
    result.qualifying.sort(key=lambda r: (r.alpha_score or 0.0), reverse=True)
    return result
