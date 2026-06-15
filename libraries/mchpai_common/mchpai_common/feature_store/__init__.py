"""Feature store — the bridge between data and models.

Designed for **scale and sequence**:

* **Schemaless** — features are a ``Map(str, float)``, so the catalog can grow
  from 500 → 1,000 → 5,000+ features without migrations.
* **Online/offline split** — Redis serves the latest vector per entity (low
  latency); MinIO holds the full history (training, backtests).
* **Point-in-time correct** — ``get_point_in_time`` returns the feature vector as
  it was *as of* a timestamp, preventing look-ahead leakage in training.
* **Sequence-native** — ``get_sequence`` returns an entity's vectors in order, so
  GNN/TFT/RL consumers get ordered trajectories, not scrambled rows.

Two backends ship here: an in-memory store (tests/dev) and a MinIO+Redis store
(production). Both implement :class:`FeatureStore`.
"""

from .store import (
    FeatureRecord,
    FeatureStore,
    InMemoryFeatureStore,
    MinioFeatureStore,
)

__all__ = ["FeatureRecord", "FeatureStore", "InMemoryFeatureStore", "MinioFeatureStore"]
