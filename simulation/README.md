# simulation/  (reserved — Phase 5, not yet built)

> Documentation of intent only. **No simulation code exists yet, and none should
> be written until First Light + the dataset milestones are met.** This directory
> reserves the architectural decision so it isn't bolted on later.

Once millions of real snapshots exist, the loop becomes:

```
   reality  ──►  simulator  ──►  models  ──►  execution
      ▲                                            │
      └────────────── feedback ────────────────────┘
```

Planned components (each consumes the *recorded reality*, never synthetic-first):

- `historical_replay/` — deterministically replay the immutable `event_log`
  through the pipeline (same reducers) to reproduce any `state(t)`.
- `paper_trading/`     — run strategies against replayed reality; no real orders.
- `monte_carlo/`       — resample observed trajectories to estimate outcome
  distributions and risk.
- `agent_based/`       — model creators/snipers/bots/retail as agents calibrated
  to observed behavior, to stress strategies against a *reactive* market.
- `adversarial/`       — red-team the system (spoofed flows, sandwiches, fake
  clusters) to find where it breaks.
- `stress_tests/`      — extreme regimes (mass rug, liquidity flash-drain,
  provider outage) for risk-control validation.

Gate to build this: **≥50k tokens, millions of snapshots, sustained GREEN quality.**
Until then: observe reality. Do not simulate it.
