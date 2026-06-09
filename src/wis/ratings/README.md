# Wallet ratings

Rank participants by observed behavior — win rate, trade multiples, Sharpe,
per-quote PnL/ROI, and the truth-weighted `alpha_score`. This is the rating
surface the scoring engine was built to feed, now fed by a translator that
captures token-to-token trades (BUG-001) and a cleaned funding graph (BUG-002).

## Pipeline

```
Source → event log → wallet_state(t) → ratings → RatingStore → leaderboard
```

```python
from wis.ratings.pipeline import rate_sources
from wis.sources import HeliusSource
ratings, store = rate_sources([HeliusSource(payloads)])
store.top(by="alpha_score", min_trades=10, min_confidence=0.3, limit=50)
```

`SqliteRatingStore` is the local reference; the schema is flat and
columnar-friendly so the *same* upserts map onto PostgreSQL/ClickHouse at
100k–millions of wallets. Only the adapter changes — the pipeline does not.

## What's honest about it

* **Every rate shows its denominator** (`closed_trades`) and `confidence`.
  Wallets below a trade/confidence floor are not ranked.
* **PnL is per quote asset** (`pnl_by_quote`) — SOL and USDC are never summed.
* **Truth-weighting tempers flash.** In the first real run, a wallet with a
  100% win rate and 21,777% ROI scored only `alpha 0.513` (near-neutral); a
  high-evidence, consistent wallet (93 trades, conf 0.82) topped alpha at 0.591.
  Raw win-rate/ROI can be artifacts; alpha is shrunk toward truth.

## What it is NOT (yet) — honest limits

* **Coverage is incomplete.** Trades priced only in SOL/USDC/USDT are captured;
  token↔token-volatile pairs (~1% of swaps) remain unpriced; quote↔quote moves
  are conversions, not trades. So PnL is a *lower bound* on activity.
* **Round-trip history is sparse in short windows.** In the first run only ~22 of
  ~4,000 observed fee payers had ≥5 closed trades — most addresses are
  counterparties or hold open positions. Real rating wants deeper per-wallet
  history (more pages) and trader-targeted discovery.
* **Data-quality artifacts exist.** FIFO matching on a partial trade stream can
  produce extreme ROIs; treat outliers as questions, not facts.
* **100k is not done here.** The sandbox has no live DB and recycles in hours;
  this runs at the thousands scale and is *designed* to scale to 100k on real
  infrastructure. `sample_leaderboard.md` is a real (small) example.

Ratings are **observation, not advice** — no position sizing, no execution.
