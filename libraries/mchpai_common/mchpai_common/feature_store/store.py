"""Feature store records, interface, and backends."""

from __future__ import annotations

import abc
import bisect
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class FeatureRecord:
    entity_type: str          # token | wallet | cluster | creator
    entity_id: str
    ts: datetime
    seq: int                  # ordering within (entity_type, entity_id)
    features: dict[str, float] = field(default_factory=dict)


class FeatureStore(abc.ABC):
    @abc.abstractmethod
    def write(self, record: FeatureRecord) -> None: ...

    def write_batch(self, records: list[FeatureRecord]) -> None:
        for r in records:
            self.write(r)

    @abc.abstractmethod
    def get_online(self, entity_type: str, entity_id: str) -> dict[str, float] | None:
        """Latest feature vector for an entity (serving path)."""

    @abc.abstractmethod
    def get_sequence(
        self, entity_type: str, entity_id: str, *, limit: int | None = None
    ) -> list[FeatureRecord]:
        """Ordered sequence of vectors for an entity (training path)."""

    @abc.abstractmethod
    def get_point_in_time(
        self, entity_type: str, entity_id: str, as_of: datetime
    ) -> dict[str, float] | None:
        """The vector in effect at ``as_of`` (no look-ahead)."""


class InMemoryFeatureStore(FeatureStore):
    """Reference implementation — exact semantics, used in tests and dev."""

    def __init__(self) -> None:
        self._seq: dict[tuple[str, str], list[FeatureRecord]] = defaultdict(list)
        self._ts_index: dict[tuple[str, str], list[float]] = defaultdict(list)

    def write(self, record: FeatureRecord) -> None:
        key = (record.entity_type, record.entity_id)
        seq = self._seq[key]
        ts = record.ts.timestamp()
        idx = bisect.bisect_right(self._ts_index[key], ts)
        seq.insert(idx, record)
        self._ts_index[key].insert(idx, ts)

    def get_online(self, entity_type: str, entity_id: str) -> dict[str, float] | None:
        seq = self._seq.get((entity_type, entity_id))
        return dict(seq[-1].features) if seq else None

    def get_sequence(
        self, entity_type: str, entity_id: str, *, limit: int | None = None
    ) -> list[FeatureRecord]:
        seq = self._seq.get((entity_type, entity_id), [])
        return seq[-limit:] if limit else list(seq)

    def get_point_in_time(
        self, entity_type: str, entity_id: str, as_of: datetime
    ) -> dict[str, float] | None:
        key = (entity_type, entity_id)
        index = self._ts_index.get(key)
        if not index:
            return None
        pos = bisect.bisect_right(index, as_of.timestamp()) - 1
        if pos < 0:
            return None
        return dict(self._seq[key][pos].features)


class MinioFeatureStore(FeatureStore):
    """Production backend: MinIO (offline history) + Redis (online latest).

    Offline layout (S3): ``features/{entity_type}/{entity_id}/{seq}.json`` —
    immutable, versioned, cheap to scan for training. Online: Redis hash
    ``feat:online:{entity_type}:{entity_id}``. The heavy I/O is intentionally
    thin here; the in-memory store defines the exact semantics this mirrors.
    """

    def __init__(self, minio_client=None, redis_client=None, bucket: str = "features") -> None:
        self._minio = minio_client
        self._redis = redis_client
        self._bucket = bucket

    def write(self, record: FeatureRecord) -> None:  # pragma: no cover - I/O
        # Production: put_object(bucket, f"{type}/{id}/{seq}.json", json(features))
        # and HSET the online latest in Redis.
        raise NotImplementedError("wire MinIO/Redis clients before use")

    def get_online(self, entity_type, entity_id):  # pragma: no cover - I/O
        raise NotImplementedError

    def get_sequence(self, entity_type, entity_id, *, limit=None):  # pragma: no cover
        raise NotImplementedError

    def get_point_in_time(self, entity_type, entity_id, as_of):  # pragma: no cover
        raise NotImplementedError
