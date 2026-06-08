"""The reality_lab tooling: diagnose what the translator did, preserve raw
payloads, and run the full observe→archive→replay→prove pipeline — all without a
network (sample payloads stand in for the live feed)."""

from __future__ import annotations

from pathlib import Path

from wis.research.reality_lab import diagnose, load_raw_session, save_raw_session
from wis.research.reality_lab.observe import run_observation

T = 1_700_000_000

# A SOL-paired buy (translates) and a token-to-token swap (does not, today).
_BUY = {
    "signature": "buy1", "timestamp": T, "type": "SWAP", "feePayer": "alpha",
    "events": {"swap": {
        "nativeInput": {"account": "alpha", "amount": "1000000000"},
        "tokenOutputs": [{"mint": "GEM", "rawTokenAmount": {"tokenAmount": "1000000000", "decimals": 6}}]}},
}
_T2T = {
    "signature": "t2t1", "timestamp": T, "type": "SWAP", "feePayer": "alpha",
    "events": {"swap": {
        "nativeInput": None, "nativeOutput": None,
        "tokenInputs": [{"mint": "USDC", "rawTokenAmount": {"tokenAmount": "5", "decimals": 6}}],
        "tokenOutputs": [{"mint": "GEM", "rawTokenAmount": {"tokenAmount": "9", "decimals": 6}}]}},
}


def test_diagnose_flags_untranslated() -> None:
    diag = diagnose([_BUY, _T2T])
    assert diag.total == 2
    assert diag.translated == 1
    untranslated = diag.untranslated()
    assert [t.signature for t in untranslated] == ["t2t1"]
    assert diag.summary() == {"transactions": 2, "translated": 1, "untranslated": 1, "events_emitted": 1}


def test_raw_session_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "raw.jsonl"
    n = save_raw_session([_BUY, _T2T], path)
    assert n == 2
    loaded = list(load_raw_session(path))
    assert [tx["signature"] for tx in loaded] == ["buy1", "t2t1"]


def test_run_observation_proves_replayable(tmp_path: Path) -> None:
    report = run_observation([_BUY, _T2T], tmp_path / "session")
    # The recording replays to identical state (the headline guarantee).
    assert report.first_light.replayable
    # Raw evidence and the event archive are both preserved.
    assert Path(report.raw_path).exists()
    assert Path(report.archive_path).exists()
    # The untranslated token-to-token swap is surfaced for the journal.
    assert len(report.diagnostics.untranslated()) == 1
