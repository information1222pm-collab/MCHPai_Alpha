# Phase 8B — External replication

The gold-standard test the project has been waiting for: do the candidate
populations recur in **fresh, independent samples** — not the same wallets
resampled, but genuinely new ones, drawn at a different time?

## Method

Three fresh active-trader sessions (`fresh_s1/s2/s3`), **150 new wallets**,
collected **~8 hours after** the original Reality-100 session (an overnight gap —
mild regime separation, not merely same-day). The original raw archive did not
survive the container's recycle (it was git-ignored), which is itself the lesson
below; replication is therefore measured against the **committed** Phase-7
profiles. Per-wallet feature tables are committed under `data/` so this analysis
is reproducible without the raw.

## Result 1 — the token-to-token dichotomy reproduces (3/3)

`frac_token_to_token` among swap-active wallets is **bimodal in every fresh
session** — a mode near 0 (SOL-paired) and a mode near 1 (router):

| session | swap-active n | bimodal? | modes | separation |
|---------|--------------:|:--------:|-------|-----------:|
| fresh_s1 | 12 ⚠ | YES | [0.00, 0.90] | 0.90 |
| fresh_s2 | 14 ⚠ | YES | [0.00, 1.00] | 1.00 |
| fresh_s3 | 13 ⚠ | YES | [0.11, 1.00] | 0.89 |

Each session's swap-active denominator is small (⚠), so any single session is
low-confidence — but the split reproduces **3/3** with separation ≈0.9 every
time. Consistent recurrence across independent samples is strong even when each
sample is thin. *The dichotomy is a property of the population, not of one draw.*

## Result 2 — the SOL-paired population reproduces as a stable cluster (3/3)

Clustering each fresh session independently (full feature set, n=53–61 wallets):

| session | SOL-paired cluster | profile | stability |
|---------|:------------------:|---------|----------:|
| fresh_s1 | YES | t2t 0.06, sol 0.94, n=8 | 0.75 |
| fresh_s2 | YES | t2t 0.00, sol 1.00, n=11 | 0.81 |
| fresh_s3 | YES | t2t 0.00, sol 0.83, n=6 | 0.53 |

Profile matches the committed Phase-7 `Cluster3` (t2t ≈ 0.05–0.06, SOL-paired).
**Isolated and stable in all three fresh sessions.**

## Result 3 — the router population reproduces in 2/3 (algorithm-sensitive)

| session | router cluster | profile | stability |
|---------|:--------------:|---------|----------:|
| fresh_s1 | YES | t2t 0.97, jupiter 0.83, n=6 | 0.84 |
| fresh_s2 | **no** | (t2t wallets present — bimodality held — but not isolated as a cluster) | — |
| fresh_s3 | YES | t2t 0.93, jupiter 0.75, n=7 | 0.79 |

Profile matches committed Phase-7 `Cluster2` (t2t ≈ 0.79–0.83, Jupiter-heavy).
Isolated in **2/3**; in session 2 the router *behavior* was present (the
bimodality held, 3/3) but did not separate into its own GMM cluster at the chosen
k — an algorithm sensitivity, not the population's absence.

## Verdict

* **The token-to-token split (structure): externally replicated, 3/3.**
* **The SOL-paired population: externally replicated, 3/3, stable, profile-consistent.**
  By the taxonomy doctrine (existence → internal stability → external replication),
  this candidate has **met the bar**.
* **The router population: supported, 2/3 as an isolated cluster** (3/3 as a
  behavior via bimodality). Strong, not yet unanimous as a discrete cluster.

## Honest caveats

* Swap-active denominators per session are small (12–14); the bimodality is
  convincing only because it recurs 3/3, not because any one session is decisive.
* ~8 hours is *mild* temporal separation, not a different market regime (e.g. a
  different week). True regime-robustness remains untested.
* Same discovery method (DEX-program fee payers) → same sampling bias as before.
* Router isolation is algorithm-sensitive (k-dependent).

## The lesson the recycle taught

The original raw archive was git-ignored and **did not survive** the container
being reclaimed. Only committed artifacts persisted. Going forward, the *analysis
inputs* (per-wallet feature tables, `data/*.csv`) and findings are committed, so
conclusions are reproducible even though the raw is ephemeral. Institutional
memory is exactly — and only — what is committed.

## Naming

Per the doctrine, the SOL-paired population has now earned the *privilege* of a
name (3/3 external replication + internal stability + bimodality). The router has
nearly earned it (2/3 as a cluster). **No name is written yet** — granting the
taxonomy's first name is a deliberate, one-way act, deferred to an explicit
decision. The clusters remain `Cluster2` / `Cluster3` until then.
