"""wallet-ingestion — turns raw transactions into wallet activity events.

Consumes the swap firehose (from the Rust engine via Redis, or directly from
Helius/Yellowstone in backfill mode), normalizes each swap into a
``WalletBoughtToken`` / ``WalletSoldToken`` event, mirrors it to the trades store,
and maintains hot wallet state in Redis for the latency-critical decision path.
"""
