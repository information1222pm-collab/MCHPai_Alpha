# The Scientific Method of MCHPAI

> **Rule 0 — Never fabricate reality.**
>
> Fake observations are the one unforgivable sin in an observational science. No
> matter how inconvenient, no matter how empty the dataset, no matter how much
> code has already been written: the system must never invent data. If reality
> is unavailable, the correct answer is **"I do not know."**

Everything else in MCHPAI is downstream of that rule. A wallet intelligence
system that will one day answer to users, investors, and stakeholders earns its
trust not by appearing certain, but by being *truthful* — including, and
especially, about what it does not know.

## Absence of data is not permission to invent data

When a universe has not been observed, its distribution is unknown. The honest
record is an empty `observations.md`, not an estimate. "We don't know yet" is
infinitely more valuable than false certainty — it is the difference between an
instrument and a rumor.

## The cycle

```
Observe  →  Replicate  →  Classify  →  Quantify  →  (only then) Optimize
```

1. **Observe.** Connect to reality through one door (a `Source`). Capture raw
   payloads *and* translated events. Prove `live_digest == replay_digest`: the
   recording must be faithful.
2. **Replicate.** One sample can lie. Measure the same quantities across
   *different* universes (active traders, random blocks, whales, dormant
   wallets). A finding is only believable when it survives replication.
3. **Classify.** Promote recurring shapes into named taxonomy classes
   (`reality_lab/taxonomy.py`). Reality becomes code.
4. **Quantify.** Measure prevalence (`reality_lab/distributions.md`,
   per-universe `observations.md`). A bug is not a binary — it is a distribution:
   `P(BUG-001 | universe)`.
5. **Only then Optimize.** A translator change is justified only by a *stable,
   replicated* measurement — and it always lands behind the replay-determinism
   contract, with a regression test built from the real payload that revealed it.

## Why this ordering is non-negotiable

* The first single-wallet sample reported `P(BUG-001) ≈ 99%`. The 100-wallet
  sample reported `59%`. Optimizing after sample #1 would have been optimizing a
  statistical lie.
* Multi-hop routing looked like it might matter; measurement said `1.3%`.
  Premature optimization would have cost weeks for a phenomenon reality calls
  negligible.
* Funding edges turned out to be `~72%` swap mechanics. Acting on the raw graph
  would have meant building intelligence on illusions.

Reality keeps correcting our assumptions. The method is what lets it.

## Institutional memory is sacred

```
Reality → Archives → Fixtures → Regression tests → Institutional memory → Knowledge
```

Most systems forget. This one remembers: every real payload that taught us
something is preserved as a fixture and pinned by a test, so a lesson learned
once is never silently unlearned. The bug journal, the taxonomy, the
distributions, and the per-universe observations are the system's memory — and
they are only ever written from reality.

## The standing answer

When asked "what's the distribution?", "what's the alpha?", "how profitable is
this?" — and the data does not yet exist — the system answers, without
embarrassment:

> **We do not know yet.**

That sentence is a feature, not a failure. It is what makes the observatory
trustworthy.
