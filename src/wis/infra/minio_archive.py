"""A replay-log archive on MinIO (S3-compatible object storage).

MinIO is where the log is preserved for the long term and where large
snapshots live. This archive serializes each stored event as a canonical JSON
object under a zero-padded, lexicographically-ordered key, so listing the bucket
yields the log *in sequence order* for free. Restoring the archive and replaying
it must reproduce the oracle's state exactly — the same vow as every other
store.

Unlike an EventStore, the archive does not *assign* sequence; it faithfully
mirrors a log that already has one. The MinIO client is imported lazily.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

from wis.eventsourcing.codec import decode_stored, encode_stored
from wis.eventsourcing.event import StoredEvent
from wis.eventsourcing.store import EventStore

_KEY_WIDTH = 20  # zero-pad sequence so lexical order == numeric order


class MinioReplayArchive:
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        *,
        bucket: str = "wis-replay",
        prefix: str = "events/",
        secure: bool = False,
    ) -> None:
        from minio import Minio  # lazy

        self._client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        self._bucket = bucket
        self._prefix = prefix
        if not self._client.bucket_exists(bucket):
            self._client.make_bucket(bucket)

    def _key(self, sequence: int) -> str:
        return f"{self._prefix}{sequence:0{_KEY_WIDTH}d}.json"

    def archive_event(self, stored: StoredEvent) -> None:
        import io

        blob = json.dumps(encode_stored(stored), sort_keys=True, separators=(",", ":")).encode()
        self._client.put_object(
            self._bucket,
            self._key(int(stored.sequence)),
            io.BytesIO(blob),
            length=len(blob),
            content_type="application/json",
        )

    def archive(self, store: EventStore) -> int:
        """Dump an entire log to the archive. Returns the count archived."""
        n = 0
        for stored in store.read():
            self.archive_event(stored)
            n += 1
        return n

    def restore(self) -> Iterator[StoredEvent]:
        """Stream the archived log back in sequence order."""
        objects = self._client.list_objects(self._bucket, prefix=self._prefix, recursive=True)
        for obj in sorted(objects, key=lambda o: o.object_name):
            resp = self._client.get_object(self._bucket, obj.object_name)
            try:
                data = json.loads(resp.read().decode())
            finally:
                resp.close()
                resp.release_conn()
            yield decode_stored(data)
