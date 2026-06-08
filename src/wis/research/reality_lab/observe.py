"""The reality observation runner — observe real wallet(s), end to end.

One command for the milestone: observe 1 wallet, then 10, then 100. It does only
what the discipline allows:

    observe → capture (raw + events) → archive → replay → prove → diagnose

It proves ``live_digest == replay_digest`` from reality, preserves the raw
provider payloads for reproduction, and reports any transaction the fixed
translator did not turn into an event — the candidates for ``bug_journal.md``.

It does NOT score, predict, or trade, and it does NOT change the translator.
Reality speaks first; refinements wait for the journal.

    python -m wis.research.reality_lab.observe --api-key $HELIUS_API_KEY \\
        --wallet <ADDRESS> [--wallet <ADDRESS> ...] --out-dir sessions/first_light
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from wis.research.reality_lab import SessionDiagnostics, diagnose, save_raw_session
from wis.sources.helius_live import (
    FirstLightResult,
    HeliusLiveTransport,
    first_light,
    observe_wallets,
)


@dataclass(frozen=True, slots=True)
class ObservationReport:
    first_light: FirstLightResult
    diagnostics: SessionDiagnostics
    raw_path: str
    archive_path: str


def run_observation(payloads: list[dict], out_dir: str | Path) -> ObservationReport:
    """Pure pipeline over already-fetched payloads (testable without a socket)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    raw_path = out / "raw_session.jsonl"
    archive_path = out / "events.jsonl"

    save_raw_session(payloads, raw_path)  # preserve the evidence
    result, _store = first_light(payloads, archive_path)  # state + replay proof
    diagnostics = diagnose(payloads)  # what reality showed vs. what we understood
    return ObservationReport(
        first_light=result,
        diagnostics=diagnostics,
        raw_path=str(raw_path),
        archive_path=str(archive_path),
    )


def _print_report(report: ObservationReport) -> None:
    fl = report.first_light
    diag = report.diagnostics
    print("=" * 72)
    print(" reality_lab — observation session")
    print("=" * 72)
    print(f"\nWallets observed : {len(fl.wallets)}  {list(fl.wallets)}")
    print(f"Events observed  : {fl.events_observed}")
    print(f"Raw session      : {report.raw_path}")
    print(f"Event archive    : {report.archive_path}")
    print(f"Replayable       : {'YES ✓' if fl.replayable else 'NO ✗'}  "
          f"(live=={fl.live_digest[:12]}…, replay=={fl.replay_digest[:12]}…)")

    s = diag.summary()
    print(f"\nDiagnostics      : {s['translated']}/{s['transactions']} translated, "
          f"{s['untranslated']} untranslated, {s['events_emitted']} events emitted")
    if diag.untranslated():
        print("\n⚠ Untranslated transactions — journal candidates (do NOT auto-fix):")
        for t in diag.untranslated():
            print(f"   sig={t.signature}  type={t.tx_type}")
        print("\n  → Record each in src/wis/research/reality_lab/bug_journal.md")
    else:
        print("\nNo untranslated transactions in this session.")
    print()


def _main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="wis.research.reality_lab.observe",
        description="Observe real wallet(s) via Helius; capture, archive, replay, prove, diagnose.",
    )
    parser.add_argument("--api-key", required=True, help="Helius API key")
    parser.add_argument("--wallet", action="append", required=True, dest="wallets", help="wallet address (repeatable)")
    parser.add_argument("--out-dir", default="sessions/first_light", help="output directory")
    parser.add_argument("--limit", type=int, default=100, help="transactions per page")
    parser.add_argument("--max-pages", type=int, default=5, help="pages per wallet")
    parser.add_argument("--base-url", default="https://api.helius.xyz", help="Helius base URL")
    args = parser.parse_args(argv)

    transport = HeliusLiveTransport(args.api_key, base_url=args.base_url)
    payloads = observe_wallets(transport, args.wallets, limit=args.limit, max_pages=args.max_pages)
    report = run_observation(payloads, args.out_dir)
    _print_report(report)
    return 0 if report.first_light.replayable else 1


if __name__ == "__main__":
    raise SystemExit(_main())
