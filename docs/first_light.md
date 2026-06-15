# First Light — The Observation Protocol

> First Light is the moment the telescope's shutter opens and the instrument
> records its first real photon. For MCHPAI, that photon is **one token birth
> observed from mainnet, with integrity.** Not a profit. Not a trade. An
> observation.

This protocol defines the milestones, how each is verified, and the go/no-go
gates between them. **No models, no trading** until the final gate.

---

## The ladder

| # | Milestone            | What it proves                                  | Verify with |
|---|----------------------|-------------------------------------------------|-------------|
| 0 | Stream connected     | Yellowstone subscribed; swaps landing on `raw.swaps` | engine metrics, `/stats` events rising |
| 1 | **1 birth**          | The full chain works end-to-end once            | `/stats` births ≥ 1; row in `token_births` |
| 2 | 10 births            | Not a fluke; discovery sources steady           | `/stats` births ≥ 10 |
| 3 | 100 births           | Sustained capture; idempotency holds (0 dups)   | quality: duplicate_births = 0 |
| 4 | 1,000 births         | Production-grade birth capture                   | quality GREEN |
| 5 | **1,000,000 snapshots** | The time-series engine is producing the gold | `/stats` snapshots ≥ 1e6 |
| 6 | 10,000 tokens        | Real corpus forming                              | `/stats` tokens ≥ 1e4 |
| 7 | 100,000 tokens       | Dataset large enough to consider models          | `/stats` tokens ≥ 1e5 |

Progress is always live: `GET /stats` (and `python scripts/first_light.py`).

---

## Go / No-Go gates

A milestone is **achieved** only if BOTH the count is met **and** the dataset
quality report (`GET /quality`, `scripts/validate_dataset.py`) is GREEN on:

- `duplicate_births == 0`
- `slot_gaps` within tolerance (backfill backlog draining, not growing)
- `replay_deterministic == true`
- `online_offline_consistent == true` (max feature divergence below tolerance)
- `snapshot_skew == 0` (seq monotonic per (mint,window); ts on window boundary)

If counts advance but quality is RED, the milestone is **NOT** achieved —
**fix integrity first.** Corrupt observations are worse than none.

---

## First Light checklist (milestone 1)

1. Pre-flight GREEN (runbook §4) with `EXECUTION_MODE=paper`.
2. Start in order (runbook §5): **persistence before ingestion**.
3. Confirm stream connected (milestone 0): `swaps_ingested` rising, no all-pool
   failover.
4. Watch `/stats`: `births` increments from 0 → 1.
5. Confirm the birth is real and well-formed:
   - `SELECT * FROM token_births ORDER BY recorded_at DESC LIMIT 1;`
   - It has `birth_slot`, `birth_timestamp`, `creator`, `launchpad`.
   - The same mint later appears in `snapshots` with monotonic `seq`.
6. Run `scripts/validate_dataset.py` → expect GREEN (trivially, at small N).

Record the timestamp, slot, and mint of First Light. **This is the moment MCHPAI
stops being an idea and becomes an instrument.**

---

## What we deliberately do NOT do yet

- No `strategy-engine` / `prediction-engine` (kept paused).
- No XGBoost — not before ~50k tokens and millions of snapshots, all GREEN.
- No new transforms, sciences, metrics-as-features, or engines.

> Reality must be allowed to speak before models are allowed to interpret.

---

## After the ladder

When milestones 4–7 are met and quality is sustained GREEN, the project earns the
right to its next phase: **dataset freeze + first XGBoost baselines**, and later
the `simulation/` harness (see `simulation/README.md`). Until then, the only job
is to observe — faithfully.
