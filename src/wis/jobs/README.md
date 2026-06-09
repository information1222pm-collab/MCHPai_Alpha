# Daily wallet scrape

A scheduled job that, every day at **midnight US/Eastern**, discovers candidate
wallets, observes them through the Helius pipeline, rates them, and keeps the
ones that are **active** (≥5 closed trades and ≥5 trades/day) with **strong**
performance (confidence-shrunk alpha ≥ 0.55 and positive primary-quote ROI).

* Schedule + CI: `.github/workflows/daily-wallet-scrape.yml`
* Logic: `daily_scrape.py` (pure filter, tested) · `runner.py` (network + CLI)

## Setup (required before it runs)

1. Add a repository **secret** `HELIUS_API_KEY` (Settings → Secrets → Actions).
   The workflow reads it; it is never committed.
2. *(Optional, for durable storage at scale)* add `WIS_PG_DSN` pointing at a
   Postgres rating store. Without it, output goes to a CSV artifact + an in-repo
   summary.
3. The workflow triggers at 04:00 **and** 05:00 UTC (to cover EST/EDT); the
   runner proceeds only during the true Eastern-midnight hour, so it runs once.
   Trigger manually anytime via *Actions → daily-wallet-scrape → Run workflow*
   (set `force: true` to bypass the time guard).

## Output

* `ratings/daily/summary-YYYY-MM-DD.md` — small, committed to the repo (history).
* `ratings/daily/wallets-YYYY-MM-DD.csv` — full list; git-ignored, uploaded as a
  90-day artifact, and upserted to Postgres if `WIS_PG_DSN` is set.

## ⚠ Honest feasibility — read this

A verified smoke run observed **250 wallets in 5.2 minutes (~48/min)** and **13
qualified**. Two consequences follow, and they matter:

1. **5,000 qualifying wallets/day is NOT achievable in a single GitHub Actions
   run.** At ~48 wallets/min a 6-hour job observes ~17k candidates; at the
   observed qualify rate that yields *hundreds*, not 5,000. Reaching 5,000/day
   requires either a **persistent worker** (not a 6h CI job) and/or a much higher
   Helius rate tier, accumulating into a **durable DB** across the day. The job
   is honest about this: it emits what qualifies within its budget and records
   `stopped_reason`; it never pads the list to hit a number.

2. **`trades_per_day` is measured over the observed window** (last ~200 txs), so
   for bursty wallets it can read in the thousands — a *recent-intensity* proxy,
   not a calendar-day rate. It is serviceable for an "active trader" filter but
   should not be read as a precise daily cadence. Likewise some ROIs are
   FIFO/translation artifacts (the truth-weighted `alpha` tempers them, which is
   why it, not raw ROI, is the headline rank).

**To actually hit 5,000/day**, the next build is: a Postgres-backed incremental
worker (cursor over discovery, dedup against already-rated wallets, accumulate
across the day), plus a higher API tier. The pieces are all here — the schedule,
the discovery, the rating, the filter, the store interface — wired to scale the
moment those two things exist.

Ratings are **observation, not advice** — no sizing, no execution.
