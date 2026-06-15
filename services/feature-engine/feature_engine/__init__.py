"""feature-engine — the platform's feature factory.

Subscribes to token/wallet/liquidity events and materializes engineered features
into ClickHouse + Redis (for serving). Feature *families* are independent plugins
(creator, liquidity, entropy, spread, attention) so the catalog can grow toward
1,000+ features without touching the core loop. Emits ``AttentionSpike`` when a
token's attention/contagion crosses a dynamic threshold.
"""
