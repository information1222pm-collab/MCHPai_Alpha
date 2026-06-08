# Philosophy

> Prices are effects. Participants are causes.

The Advanced Wallet Intelligence System exists to understand the **causes**. It
studies who acts, how well, with whom, and how that changes over time. Price is
downstream; participants are upstream. We model upstream.

## Reality and observation have priority over prediction

The system is an **observatory** before it is an oracle. We measure what
demonstrably happened before we forecast anything. When a metric requires data we
have not ingested, it reports `None` — *honest absence* — rather than a confident
fabrication. A half-truth dressed as a number is worse than a clear "not yet
known."

## Wallets are movies, not snapshots

A wallet is `wallet_state(t)`: an evolving entity, not a static address. Sequence
information is preserved everywhere. The most important questions are about
*change* — when did this participant's character shift? `sequence_lab` exists
specifically to watch the movie, frame by frame.

## Determinism is a moral stance

If we cannot reproduce a conclusion, we cannot trust it. The same event log must
always reconstruct the same state — exactly, forever. That is why money is exact,
folds are pure, and replay is deterministic. Reproducibility is what separates
intelligence from anecdote.

## Optimize scores for truth, not profitability

It would be easy to fit scores to past returns. We refuse. Scores answer "how
strongly does the evidence support this quality?" and are shrunk toward neutral
when the sample is thin. We are not building a leaderboard of lucky gamblers; we
are building a faithful compression of behavior.

## Build the observatory first

No execution. No copy trading. No position sizing. Those may emerge later, *from*
the intelligence — but they are not the point, and pretending otherwise would
corrupt the data and the incentives. Understanding is the deliverable.

## A confidence interval is humility, quantified

We report estimates with their error, denominators with their rates, and "we do
not know yet" when reality has not spoken. A point estimate that hides its
uncertainty is a small lie; an interval is the truth about how much we actually
know. See `docs/STATISTICS.md` and `docs/SCIENTIFIC_METHOD.md`.

## Populations, not "the market"

There is no single distribution to discover. `P(BUG-001)` measured 8.7%, 15.8%
and 59.1% across populations — and decomposed further into latent behavioral
classes within a single label. We do not impose human categories ("active
trader") onto reality; we discover the categories reality already has, and
condition every question on the *discovered* population: `P(X | population)`.

## Evidence suggests; it does not obligate

Evidence may suggest directions. It does not obligate them. The variance hinted at
latent populations; the populations hint at a behavioral embedding; the embedding
hints at dynamics and, one day, probability. These are whispers, not mandates.
Future maintainers inherit *questions*, not a prophecy — and the right response to
a whisper reality has not yet repeated is to wait, not to build.

## Designed for decades

Event types are versioned and appended, never renamed in place. Adapters depend
on the core, never the reverse. The catalog of features and labs grows; the
architecture that carries them stays still. We are writing code that a successor
ten years from now can replay, audit, and extend.
