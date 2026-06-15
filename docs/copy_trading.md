# Copy Trading & Position Sizing

MCHPAI does not blindly mirror wallets. It copies *predicted* smart-money buys,
sized by edge and risk, gated by safety.

## Signal → order

1. `prediction-engine` emits `BuySignalGenerated` when the gate holds:
   `buy_probability ≥ τ_p` **and** `expected_value ≥ τ_ev` **and**
   `risk_score ≤ τ_risk` (thresholds in `.env`).
2. `strategy-engine` sizes it and emits an `Order` to `exec.orders`.
3. `execution-engine` (Rust) applies a defensive size guard and submits.

## Adaptive position sizing

(`services/strategy-engine/strategy_engine/sizing.py`) — fractional Kelly with
caps:

```
edge      = clamp(EV_bps / 10_000, 0, edge_cap)
kelly_f   = edge / variance_estimate
size_sol  = bankroll · kelly_fraction · kelly_f
                     · conviction_multiplier   # 0.5x..1.5x from copied wallet/cluster
                     · (1 - risk_score/100)    # shrink for risky tokens
size_sol  = clamp(size_sol, min_ticket, min(max_ticket, 2% of liquidity, remaining_exposure))
```

* **Conviction multiplier** leans in when strong, proven money leads.
* **Risk shrink** scales down for structurally risky tokens.
* **Liquidity cap** prevents self-impact on thin pools.
* **Exposure cap** bounds per-token concentration.

The Rust engine re-applies a risk shrink + hard ceiling (`execution/sizing.rs`)
as defense-in-depth, so a stale/bad upstream value can never blow the bankroll.

## Risk controls / kill-switches

* Per-trade max, per-token exposure cap, **daily loss limit** → auto-pause.
* Global pause flag `exec:paused` in Redis, honored every loop by the engine and
  the strategy-engine; flippable from the API (`/control/pause`).
* **Token safety gate** (`risk_score`): mint/freeze authority, LP burn, top-holder
  concentration, honeypot simulation.
* **Paper mode** (`EXECUTION_MODE=paper`): full pipeline, no signing — logs the
  intended trade. Default until you flip to `live`.

## Why "predict" not "mirror"

By the time a copy of an on-chain buy lands, the naive mirror is late. MCHPAI uses
wallet + cluster behavior to estimate the buy *as it forms* and to act with a
latency and sizing edge — see [execution_engine](execution_engine.md).
