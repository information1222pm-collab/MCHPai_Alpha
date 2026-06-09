"""Wallet ratings — rank participants by observed behavior.

The rating engine the system was built for, finally fed by a translator that
captures token-to-token trades (BUG-001) and a funding graph cleaned of swap
mechanics (BUG-002). Every rating reports its **denominator** (closed trades) and
its **confidence** (Statistics doctrine); PnL is kept **per quote asset** so SOL
and USDC are never silently summed. Ratings are observation, not advice — no
position sizing, no execution.

Designed to scale: ratings flow into a :class:`RatingStore` (SQLite locally,
ready to swap for PostgreSQL/ClickHouse), so the same pipeline that rates a few
thousand wallets here rates millions on real infrastructure.
"""
