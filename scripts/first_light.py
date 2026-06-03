#!/usr/bin/env python3
"""First Light milestone tracker.

Reads the observatory progress counters from Redis and prints the milestone
ladder with achieved/pending status. A milestone is only "achieved" when its
count is met AND the latest quality report is not RED (see docs/first_light.md).
"""

from __future__ import annotations

import json
import sys

LADDER = [
    ("1 birth", "stats:births", 1),
    ("10 births", "stats:births", 10),
    ("100 births", "stats:births", 100),
    ("1,000 births", "stats:births", 1_000),
    ("1,000,000 snapshots", "stats:snapshots", 1_000_000),
    ("10,000 tokens", "stats:tokens", 10_000),
    ("100,000 tokens", "stats:tokens", 100_000),
]


def main() -> int:
    from mchpai_common.database import get_redis

    rds = get_redis()
    quality = rds.get("quality:report")
    q_status = json.loads(quality)["status"] if quality else "UNKNOWN"
    blocked = q_status == "RED"

    print(f"Dataset quality: {q_status}" + ("  (RED → milestones blocked)" if blocked else ""))
    print("-" * 52)
    counts: dict[str, int] = {}
    for label, key, target in LADDER:
        if key not in counts:
            counts[key] = int(rds.get(key) or 0)
        cur = counts[key]
        met = cur >= target and not blocked
        bar = "✅" if met else ("⏳" if cur > 0 else "·")
        pct = min(100.0, 100.0 * cur / target)
        print(f"{bar} {label:<22} {cur:>12,} / {target:<12,} ({pct:5.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
