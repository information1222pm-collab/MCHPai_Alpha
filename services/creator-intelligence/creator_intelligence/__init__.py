"""creator-intelligence — scores the wallets that mint tokens.

Aggregates every creator's launch history (from `tokens` + `ground_truth` +
ClickHouse volume/buyer stats) into a `CreatorProfile` and `creator_score`, then
persists it. A creator's track record is one of the strongest priors for
rug/survival prediction, so this score is a first-class model feature.
"""
