# reality_lab

Where MCHPAI sees the universe instead of imagining it.

This lab connects the observatory to a real feed and records what reality —
not speculation — reveals. It does not refine the translator; it observes,
proves replayability, and journals issues for later, evidence-driven fixes.

## Discipline

* **No hypothetical fixes.** `translate_helius` is held fixed. We change it only
  after [`bug_journal.md`](bug_journal.md) shows a real, recurring issue.
* **Reality speaks first.** Observe 1 wallet, then 10, then 100. Let the data set
  the priorities.
* **Truth stays stable.** `translate_helius()` is isolated from `wallet_state(t)`,
  and every observed session proves `live_digest == replay_digest`. The recording
  is faithful even when the translation is incomplete.

## Run an observation session

```bash
export HELIUS_API_KEY=...        # provided out-of-band; never committed
python -m wis.research.reality_lab.observe \
    --api-key "$HELIUS_API_KEY" \
    --wallet <ADDRESS> [--wallet <ADDRESS> ...] \
    --out-dir sessions/first_light
```

It will:

1. **Observe** the wallet(s) via Helius Enhanced Transactions.
2. **Capture** raw provider payloads (`raw_session.jsonl`) *and* translated
   domain events (`events.jsonl`).
3. **Replay** the event archive and **prove** the recording is bit-identical to
   the live state (`live_digest == replay_digest`).
4. **Diagnose** every transaction the translator produced nothing for, and list
   them as bug-journal candidates.

It prints only **facts** — closed trades, lifetime ROI, DNA, replayability. No
alpha, no scores, no prediction.

Session artifacts (`sessions/`, raw payloads) are git-ignored: real wallet data
is reproducible from the chain and is not source. The journal entries and the
small regression fixtures under `tests/fixtures/helius/` *are* committed — they
are the institutional memory.

## First Light #1 (2026-06-08)

The first real session immediately revealed two genuine issues (see the journal):
router/token-to-token swaps produce no trade events, and incidental SOL transfers
become spurious funding edges. Neither was top of a hypothetical to-do list —
which is exactly why we waited for reality to choose the problems.
