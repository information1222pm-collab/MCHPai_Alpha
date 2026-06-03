"""prediction-engine — turns intelligence into decisions.

Consumes attention spikes, cluster detections, and feature vectors; computes the
five headline scores (wallet_alpha_score, cluster_score, buy_probability,
expected_value, risk_score); and emits ``PredictionGenerated`` plus, when the
decision gate is crossed, ``BuySignalGenerated``.

Models are loaded from the MinIO model registry via a backend-agnostic
:class:`ModelRegistry`; gradient-boosted trees today, GNNs/transformers later —
the serving interface does not change.
"""
