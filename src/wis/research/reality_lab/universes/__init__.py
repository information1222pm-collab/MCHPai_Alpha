"""Universes — the populations we replicate measurements across.

One sample can lie. Replication across *different* universes — active traders,
random blocks, whales, dormant wallets — is how we learn whether a finding (say,
``P(BUG-001) = 59%``) is a property of reality or an artifact of how we sampled.

This package is an **instrument**, not a result. It defines, as code:

* the :class:`Universe` registry — each population's discovery method and its
  honest, documented biases;
* pure discovery *parsers* (fee payers from a block, from enhanced txs) that can
  be tested without a network.

It deliberately contains **no observations**. Measured distributions live in each
universe's ``observations.md``, and only after real data is collected. Rule 0
(see ``docs/SCIENTIFIC_METHOD.md``): never fabricate reality. An empty universe
is correct; an invented one is not.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

# Solana Vote program — its transactions are consensus noise, never trades.
_VOTE_PROGRAM = "Vote111111111111111111111111111111111111111"


@dataclass(frozen=True, slots=True)
class Universe:
    key: str          # short label, e.g. "A"
    slug: str         # directory name, e.g. "active_traders"
    title: str
    status: str       # "observed" | "awaiting_first_light" | "requires_characterization"
    discovery: str    # how wallets are sampled
    biases: tuple[str, ...]


# The eight universes. Status reflects reality as of this commit: only
# active_traders has been observed (the Reality-100 archive). The rest are
# instrument-ready and awaiting First Light — no data is invented for them.
UNIVERSES: tuple[Universe, ...] = (
    Universe(
        "A", "active_traders", "Active traders", "observed",
        "Fee payers of recent transactions on six DEX programs, then each wallet's recent history.",
        ("skews to active DEX traders", "Jupiter over-represented (used in discovery)",
         "single session; not time-diversified"),
    ),
    Universe(
        "B", "random_blocks", "Random recent blocks", "observed",
        "Sample recent confirmed blocks (RPC getBlock); take fee payers of non-vote transactions.",
        ("over-represents whatever is on-chain now (MEV/HFT bots)",
         "fee payers may be relayers/programs, not end users", "point-in-time snapshot"),
    ),
    Universe(
        "C", "random_wallets", "Random wallets", "awaiting_first_light",
        "From random recent blocks, select random distinct system-owned signers.",
        ("'random' is conditioned on recent activity — dormant wallets invisible",
         "no balance/age stratification"),
    ),
    Universe(
        "D", "high_pnl", "High-PnL wallets", "requires_characterization",
        "Two-stage: sample candidates, observe into wallet_state(t), rank by realized PnL, keep top decile.",
        ("survivorship — only wallets with closed trades qualify",
         "depends on translator coverage (BUG-001 hides token-to-token PnL today)",
         "measures OUR PnL estimate, not ground truth"),
    ),
    Universe(
        "E", "pumpfun", "Pump.fun participants", "observed",
        "Fee payers of recent pump.fun program transactions.",
        ("memecoin-launch population: high churn, many one-shot wallets", "bot-heavy",
         "recent-activity survivorship"),
    ),
    Universe(
        "F", "old_wallets", "Old wallets", "requires_characterization",
        "Two-stage: discover candidates, page getSignaturesForAddress to oldest signature; keep wallets older than a cutoff.",
        ("old != active — sparse recent data", "expensive to page to genesis",
         "discovery still conditioned on some activity"),
    ),
    Universe(
        "G", "large_wallets", "Large wallets", "observed",
        "Two-stage: discover candidates, getBalance, keep top holders by SOL balance (>= 10 SOL).",
        ("SOL balance != trading size (custody/treasury/CEX)", "large holders may rarely trade",
         "ignores value held in tokens"),
    ),
    Universe(
        "H", "dormant_wallets", "Dormant wallets", "requires_characterization",
        "Two-stage: discover candidates, keep those with no activity in the last N days.",
        ("fundamentally hard to sample — recent-activity discovery cannot see them",
         "requires a pre-existing wallet universe", "'dormant' threshold is arbitrary"),
    ),
)

BY_SLUG: dict[str, Universe] = {u.slug: u for u in UNIVERSES}


# ---------------------------------------------------------------------------
# Pure discovery parsers (the testable parts of the telescope)
# ---------------------------------------------------------------------------


def fee_payers_from_enhanced(txs: Iterable[dict]) -> list[str]:
    """Distinct fee payers from Helius enhanced transactions, order-preserving."""
    seen: list[str] = []
    s: set[str] = set()
    for tx in txs:
        fp = tx.get("feePayer")
        if fp and fp not in s:
            s.add(fp)
            seen.append(fp)
    return seen


def _account_key(k: object) -> str | None:
    # accountKeys may be plain strings (encoding=json) or objects (jsonParsed).
    if isinstance(k, str):
        return k
    if isinstance(k, dict):
        return k.get("pubkey")
    return None


def fee_payers_from_block(block: dict) -> list[str]:
    """Distinct fee payers (first account key) of non-vote transactions in an RPC
    getBlock result. Pure; tolerant of json / jsonParsed encodings."""
    seen: list[str] = []
    s: set[str] = set()
    for entry in block.get("transactions", []):
        msg = (entry.get("transaction") or {}).get("message") or {}
        keys = [k for k in (_account_key(k) for k in msg.get("accountKeys", [])) if k]
        if not keys or _VOTE_PROGRAM in keys:
            continue
        payer = keys[0]
        if payer not in s:
            s.add(payer)
            seen.append(payer)
    return seen
