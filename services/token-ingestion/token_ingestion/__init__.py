"""token-ingestion — discovers newly created tokens across all sources.

Sources (Pump.fun, Raydium, Meteora, Birdeye, Jupiter, Helius, Yellowstone) are
normalized behind a common :class:`Source` interface and fan into a single
``TokenCreated`` / ``TokenSnapshot`` event stream. Adding a venue = adding one
Source subclass; nothing downstream changes.
"""
