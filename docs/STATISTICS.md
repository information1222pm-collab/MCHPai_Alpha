# Statistics doctrine

The observatory reports numbers about reality. These rules keep those numbers
honest. They are not style preferences — they are the difference between an
instrument and a rumor.

## Rule 1 — Every rate reveals its denominator

A percentage without its denominator is not a measurement. `20%` over 5 swaps
and `20%` over 5,000 swaps are different facts wearing the same mask. Every rate
the system reports carries the `n` it was computed over.

## Rule 2 — `n < 100` is low confidence

Below ~100 events a proportion is noisy enough to mislead. Such rates are
**flagged** (⚠) wherever they appear. The first lesson of this project: a
single-wallet sample said `P(BUG-001) ≈ 99%`; it was 1 unlucky denominator away
from the truth. (`reality_lab.reproduce.LOW_CONFIDENCE_N`.)

## Rule 3 — Confidence intervals matter

A point estimate without an interval pretends to a precision it does not have.

* For a single proportion, use the **Wilson interval** (`wilson_interval`) — it
  stays sane at small `n` where the naive Wald interval produces nonsense.
* For *reproducibility* — does a rate hold across fresh samples? — run multiple
  trials and report the **across-trial mean ± t-interval** (`summarize`). This
  interval captures the variance introduced by *which wallets we sampled*, which
  is exactly the question reproducibility asks.

Report both when available: the pooled Wilson interval is the best point
estimate; the across-trial interval tells you whether it reproduces.

## Rule 4 — Unknown is preferred over false precision

If reality has not been observed, the answer is **"we do not know yet"** — an
empty `observations.md`, a `—` in the ledger — never an estimate dressed as a
fact. This is Rule 0 of `SCIENTIFIC_METHOD.md` expressed in numbers.

## Rule 5 — Populations, not "the market"

There is no single distribution. `P(BUG-001)` measured at 8.7% (large wallets),
15.8% (pump.fun) and 59.1% (active traders) is not three noisy readings of one
number — it is three different populations behaving differently. Always condition
on the universe: report `P(X | universe)`, never a context-free `P(X)`.

## Practice

* `reality_lab.replicate.render_markdown` prints denominators and flags `n < 100`.
* `reality_lab.reproduce.summarize` / `wilson_interval` compute the intervals.
* Per-universe reproducibility lives in `reality_lab/reproducibility.md`.
* Raw sessions are archived (institutional memory) so any interval can be
  recomputed and audited.

> A confidence interval is humility, quantified.
