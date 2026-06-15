# Dataset Validation — Does Reality Agree?

> This work matters more than ML. An instrument that lies is worse than no
> instrument. Every question below has a concrete check in
> `mchpai_common.quality` and is run by `scripts/validate_dataset.py`.

The validator produces a `DatasetQualityReport` (status GREEN/YELLOW/RED), writes
it to Redis `quality:report`, and surfaces it at `GET /quality`.

---

## The questions (and how we answer them)

### 1. Missing swaps?
Compare observed swap/event counts against expected coverage implied by the slot
range actually processed. Large unexplained shortfalls → investigate ingestion /
parser drops. *Check:* `coverage(expected, observed)`.

### 2. Slot gaps?
The Rust `SlotTracker` records gaps; the reconciler backfills them. The validator
reads gap totals and the backfill backlog. *Healthy:* backlog draining, not
growing. *Check:* `find_slot_gaps(slots)` / gap counters.

### 3. Duplicate births?
The birth registry is idempotent, so this **must be 0**. Any duplicate indicates
a write-path bug. *Check:* `find_duplicate_births(mints)` (RED if > 0).

### 4. Snapshot skew?
Per `(mint, window)`, `seq` must be strictly monotonic and `ts` must align to the
window boundary. *Check:* `sequence_integrity(seqs)` + boundary alignment.

### 5. Feature leakage?
The Feature Factory's `compute_sequence` must be **causal**: a feature at step *t*
must not change if a *future* row changes. *Check:* `assert_causal(compiler, rows)`
perturbs a future row and asserts past features are unchanged. RED on any change.

### 6. Creator contamination?
A creator's record at decision time must not include outcomes that resolved
*after* that time (no future leakage via `creator_state`). *Check:* verify
`creator_state(t)` monotonic and that training joins use point-in-time reads.

### 7. Replay determinism?
Re-running pure reducers over the same ordered events must yield identical state.
*Check:* `replay_consistent(events, build_reducer, apply)` (RED if divergent).

### 8. Online/offline consistency?
The live feature vector (`feat:vec`) and the offline-recomputed vector for the
same step must match within tolerance. *Check:* `online_offline_divergence(a, b)`
→ max abs diff below `tol` (default 1e-6 for identical catalogs).

### 9. Time synchronization?
Host clock drift < 250 ms; chain `block_time` authoritative for swaps; snapshot
`ts` on window boundaries. *Check:* boundary alignment + drift probe.

---

## Quality metrics (observatory health)

`mchpai_common.quality.metrics`:

- **Event completeness** — observed / expected.
- **Snapshot coverage** — tokens with ≥1 snapshot / tokens born.
- **Feature null rate** — per-feature share of null/zero across a sample.
- **Label maturity** — fraction of `ground_truth.is_final`.
- **Feature drift / distribution shift** — **PSI** (Population Stability Index)
  of each feature vs. a reference window. PSI < 0.1 stable, 0.1–0.25 moderate,
  > 0.25 significant shift.

These make the *health of the observatory itself observable* — tracked over time
just like the data it collects.

---

## Status rollup

`DatasetQualityReport.status`:

- **RED** — any hard-integrity failure: duplicate births, replay divergence,
  feature leakage, online/offline mismatch, snapshot skew. **Blocks milestones.**
- **YELLOW** — soft concerns: elevated null rates, moderate PSI drift, slot-gap
  backlog present but draining, label maturity low (expected early).
- **GREEN** — all hard checks pass; soft metrics within thresholds.

Milestone advancement (and, later, model training) requires **GREEN**.
