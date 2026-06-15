"""persistence — durability & reality-capture layer.

Three jobs, all about never losing reality:
  1. **Sacred births**: every ``TokenCreated`` is written immutably to
     `token_births` (idempotent; never overwritten).
  2. **Immutable event log**: every envelope on the bus is appended to ClickHouse
     `event_log` for full replay/audit.
  3. **Progress counters**: Redis + Prometheus counters that track the march to
     1M snapshots / 10k / 100k tokens.
"""
