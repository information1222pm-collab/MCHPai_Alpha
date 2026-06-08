# Event catalog

Every fact in the system is one of these events. The names match the system
charter. Events are immutable and versioned (`event_version`); the schema evolves
by **appending** new event types or bumping a version — never by renaming or
repurposing an existing one, so historical replay stays valid for decades.

Two families:

## Ingestion events — causes observed from the world

| Event | Meaning | Key fields |
|-------|---------|-----------|
| `WalletCreated` | first awareness a wallet exists | `wallet`, `funded_by?` |
| `WalletFunded` | a funding flow between wallets | `source`, `target`, `amount` |
| `WalletBoughtToken` | a wallet acquired `base` for `quote` | `wallet`, `token`, `base`, `quote` |
| `WalletSoldToken` | a wallet disposed of `base` for `quote` | `wallet`, `token`, `base`, `quote` |
| `TokenPriceObserved` | a market price at a point in time | `token`, `price_quote_per_base` |
| `WalletUpdated` | non-trade attribute/label change | `wallet`, `attributes` |

`WalletFunded` and `TokenPriceObserved` are additions to the charter's named set,
required by the graph (funding trees) and timing (price-percentile) intelligence
respectively. They are ingestion facts, not conclusions.

## Derived events — conclusions emitted by the system's own reasoning

The platform writes its conclusions **back into the log** so that intelligence is
itself replayable, not a side effect hidden in a database.

| Event | Meaning |
|-------|---------|
| `WalletStateUpdated` | `wallet_state(t)` advanced (closed trades / open positions) |
| `WalletAlphaUpdated` | a wallet's alpha score was recomputed |
| `ClusterDetected` | a new community emerged from `graph(t)` |
| `ClusterUpdated` | a cluster's membership evolved (`joined` / `left`) |
| `GraphUpdated` | `graph(t)` recomputed (nodes, edges, density, clusters) |
| `WalletProfileGenerated` | a Wallet DNA profile was produced |

## Envelope

When appended, every event is wrapped in a `StoredEvent` with:

* `sequence` — global, gap-free, strictly increasing (assigned by the store)
* `ingestion_time` — when we learned the fact (drives point-in-time reads)
* `event_id` — deterministic, content-addressed
* `payload` — the `DomainEvent` above

The producer never sets envelope metadata; the store owns it. This is what makes
ordering and leak-free reads trustworthy.
