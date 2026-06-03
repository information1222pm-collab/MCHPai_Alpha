"""state-engine — records entities as evolving sequences (`state(t)`).

Drives the timeline reducers from the live event stream and appends each emitted
state to ClickHouse: `wallet_states`, `creator_states`, `graph_states`. These
append-only trajectories are the training substrate for wallet/creator
transformers and temporal GNNs.
"""
