"""reality_lab — where the system meets the universe instead of imagining it.

This lab does not *fix* reality. It *observes* it, and makes every observed
problem reproducible and recordable. Engineering discipline over capability:
we solve only the problems reality reveals, never the ones we imagine.

Two responsibilities:

* **Preserve the raw.** A live session is captured twice — as domain events (for
  the log and replay) and as the *raw provider payloads* (so any translation
  issue can be reproduced from source and pasted into the bug journal).
* **Diagnose, don't decide.** :func:`diagnose` reports, per transaction, what the
  translator produced — and flags transactions that produced *nothing*. An
  untranslated transaction is not a bug to be silently fixed; it is an
  observation to be journaled, understood, and only then addressed.

The translator (:func:`wis.sources.helius_source.translate_helius`) is held
fixed on purpose. Reality can be ugly; truth stays stable. Every future fix
lands behind the replay-determinism contract — never ahead of an observation.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from wis.sources.helius_source import translate_helius

# ---------------------------------------------------------------------------
# Preserve the raw provider payloads (for reproduction in the bug journal)
# ---------------------------------------------------------------------------


def save_raw_session(payloads: Iterable[dict], path: str | Path) -> int:
    """Persist raw provider payloads verbatim, one JSON object per line. This is
    the evidence: the exact bytes reality sent, kept so any issue is reproducible."""
    n = 0
    with Path(path).open("w", encoding="utf-8") as fh:
        for tx in payloads:
            fh.write(json.dumps(tx, sort_keys=True, separators=(",", ":")))
            fh.write("\n")
            n += 1
    return n


def load_raw_session(path: str | Path) -> Iterator[dict]:
    """Re-read a raw session for reproduction and diagnosis."""
    with Path(path).open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


# ---------------------------------------------------------------------------
# Diagnose: report what the translator did, flag what it ignored
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TxDiagnostic:
    signature: str | None
    tx_type: str | None
    event_count: int
    event_types: tuple[str, ...]

    @property
    def untranslated(self) -> bool:
        """Produced no domain events — an observation worth journaling, not a
        silent drop."""
        return self.event_count == 0


@dataclass(frozen=True, slots=True)
class SessionDiagnostics:
    transactions: tuple[TxDiagnostic, ...]

    @property
    def total(self) -> int:
        return len(self.transactions)

    @property
    def translated(self) -> int:
        return sum(1 for t in self.transactions if not t.untranslated)

    @property
    def events_emitted(self) -> int:
        return sum(t.event_count for t in self.transactions)

    def untranslated(self) -> list[TxDiagnostic]:
        """The transactions reality presented that we did not yet understand —
        the raw material of the bug journal."""
        return [t for t in self.transactions if t.untranslated]

    def summary(self) -> dict[str, int]:
        return {
            "transactions": self.total,
            "translated": self.translated,
            "untranslated": len(self.untranslated()),
            "events_emitted": self.events_emitted,
        }


def diagnose(payloads: Iterable[dict]) -> SessionDiagnostics:
    """Run the (fixed) translator over raw payloads and report, never altering
    behavior. The untranslated set is the honest record of what reality showed
    us that the current translator does not yet handle."""
    rows: list[TxDiagnostic] = []
    for tx in payloads:
        events = translate_helius(tx)
        rows.append(
            TxDiagnostic(
                signature=tx.get("signature"),
                tx_type=tx.get("type"),
                event_count=len(events),
                event_types=tuple(e.EVENT_TYPE for e in events),
            )
        )
    return SessionDiagnostics(transactions=tuple(rows))
