"""snapshot-engine — builds the ordered time-series backbone of the platform.

Consumes the swap stream and a token's birth event, maintains a
:class:`MultiWindowAggregator` per mint (5s/15s/30s/60s), labels each closed
window with a lifecycle phase, writes the rich snapshot to ClickHouse, and
re-publishes it as ``TokenSnapshot`` for downstream consumers.

Sequence integrity is the contract: every snapshot has a monotonic ``seq`` and
``age_seconds``, so a token's full birth→death trajectory can be replayed in
order for sequence learning.
"""
