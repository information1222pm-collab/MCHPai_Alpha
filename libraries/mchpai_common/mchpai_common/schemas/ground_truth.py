"""Ground-truth label schema — the foundation of all supervised learning.

Every token eventually accrues a label record: which return multiples it achieved
within which horizons, and a terminal outcome (rugged / survived / viral). These
are computed *after the fact* from the snapshot sequence by the ground-truth
service, then frozen — they are the targets every model trains against.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# return multiples and horizons we label against
MULTIPLES = (2, 5, 10, 25, 100)
HORIZONS = ("1h", "6h", "24h", "7d")
HORIZON_SECONDS = {"1h": 3600, "6h": 21600, "24h": 86400, "7d": 604800}


class Outcome(str, Enum):
    pending = "pending"     # still within observation window
    rugged = "rugged"       # liquidity pulled / price → 0
    survived = "survived"   # alive past 7d without rug
    viral = "viral"         # achieved >=10x and sustained attention


class GroundTruth(BaseModel):
    mint: str
    created_at: datetime
    reference_price: float | None = None      # baseline (birth) price in SOL

    # achieved_{mult}x_{horizon} flags, e.g. achieved["10x"]["24h"] = True
    achieved: dict[str, dict[str, bool]] = Field(default_factory=dict)

    max_multiple: float = 1.0                  # peak price / reference
    time_to_max_seconds: float | None = None
    max_multiple_by_horizon: dict[str, float] = Field(default_factory=dict)

    outcome: Outcome = Outcome.pending
    rugged_at: datetime | None = None
    survival_seconds: float | None = None
    holder_retention: float | None = None      # holders_now / holders_peak

    labeled_at: datetime | None = None
    is_final: bool = False                     # True once 7d window closed

    def label(self, mult: int, horizon: str) -> bool:
        return self.achieved.get(f"{mult}x", {}).get(horizon, False)
