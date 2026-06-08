"""Infrastructure adapters.

The intelligence core defines *protocols* (e.g. :class:`~wis.eventsourcing.store.EventStore`);
this package will hold the production implementations that satisfy them against
real systems — NATS JetStream + MinIO for the event log, PostgreSQL and
ClickHouse for projections, Neo4j for the graph, Redis for hot online state.

Two rules keep the architecture honest for decades:

1. **Adapters depend on the core, never the reverse.** Nothing in
   ``wis.domain`` / ``wis.eventsourcing`` / ``wis.features`` imports anything
   here. Swap a database without touching a single line of intelligence.
2. **Every adapter is verified against the in-memory reference.** The
   :class:`~wis.eventsourcing.store.InMemoryEventStore` is the oracle; a
   production store is correct iff it produces identical replays.

Only configuration lives here today; concrete clients are added as the platform
is deployed, each behind the protocol it implements.
"""
