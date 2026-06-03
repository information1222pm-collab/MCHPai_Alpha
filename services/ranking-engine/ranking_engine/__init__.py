"""ranking-engine — maintains live leaderboards.

Periodically ranks wallets by ``wallet_alpha_score`` and clusters by
``cluster_score`` into a Redis sorted set (served instantly by api-gateway) and
snapshots them to Postgres for history.
"""
