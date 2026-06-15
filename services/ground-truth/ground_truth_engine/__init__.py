"""ground-truth-engine — manufactures the labels every model learns from.

Periodically pulls each token's 60s snapshot sequence from ClickHouse, computes
the multiples-achieved-per-horizon matrix and terminal outcome, and freezes the
result in Postgres `ground_truth`. Pending tokens are re-labeled until their 7d
window closes (`is_final`), after which they never change — guaranteeing leak-free
training targets.
"""
