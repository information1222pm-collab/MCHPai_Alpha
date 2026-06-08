"""Replication harness — turn a sample of reality into a measured distribution.

Replication is the heart of Phase 5: one sample can lie (the first wallet said
BUG-001 was 99%; 100 wallets said 59%). The cure is to measure the *same*
quantities across *different* universes and compare. This module provides the
pure measurement — ``measure(payloads) -> UniverseDistribution`` — so every
universe is quantified identically, and the bugs themselves become
distributions: ``P(BUG-001 | universe)``, ``P(BUG-002 | universe)``.

Pure and streaming: it reads payloads once, classifies via the taxonomy, and
never changes translation. The same instrument measures active traders, random
blocks, whales and dormant wallets alike.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field

from wis.research.reality_lab import taxonomy as tax
from wis.sources.helius_source import translate_helius

# Native-transfer classes that are swap mechanics, not genuine funding (BUG-002).
_MECHANICS = {tax.NativeTransferClass.DUST, tax.NativeTransferClass.ATA_RENT, tax.NativeTransferClass.SELF}
_TRADE_EVENTS = {"WalletBoughtToken", "WalletSoldToken"}


@dataclass(slots=True)
class UniverseDistribution:
    n_transactions: int = 0
    type_counts: Counter = field(default_factory=Counter)
    n_parsed_swaps: int = 0
    swap_shape_counts: Counter = field(default_factory=Counter)
    swap_source_counts: Counter = field(default_factory=Counter)
    multi_hop_swaps: int = 0
    n_native_transfers: int = 0
    native_class_counts: Counter = field(default_factory=Counter)
    zero_event_txs: int = 0
    swaps_with_trade: int = 0
    trade_events: int = 0
    funding_events: int = 0

    # -- derived rates (the comparable quantities) -------------------------

    def share(self, count: int, total: int) -> float:
        return count / total if total else 0.0

    @property
    def p_bug_001(self) -> float:
        """P(token-to-token | parsed swap) — the dominant untranslated shape."""
        return self.share(self.swap_shape_counts.get(tax.SwapShape.TOKEN_TO_TOKEN, 0), self.n_parsed_swaps)

    @property
    def p_swap_untranslated(self) -> float:
        """P(no trade event | parsed swap) — the full swap-ignorance rate."""
        return 1.0 - self.share(self.swaps_with_trade, self.n_parsed_swaps)

    @property
    def p_bug_002_mechanics(self) -> float:
        """P(swap-mechanics | native transfer) — dust + rent + self."""
        mech = sum(self.native_class_counts.get(c, 0) for c in _MECHANICS)
        return self.share(mech, self.n_native_transfers)

    @property
    def p_zero_event_tx(self) -> float:
        return self.share(self.zero_event_txs, self.n_transactions)

    @property
    def funding_trade_ratio(self) -> float:
        return self.funding_events / self.trade_events if self.trade_events else float("inf")

    @property
    def multi_hop_rate(self) -> float:
        return self.share(self.multi_hop_swaps, self.n_parsed_swaps)


def measure(payloads: Iterable[dict]) -> UniverseDistribution:
    d = UniverseDistribution()
    for tx in payloads:
        d.n_transactions += 1
        d.type_counts[tx.get("type")] += 1

        if (tx.get("events") or {}).get("swap"):
            d.n_parsed_swaps += 1
            d.swap_shape_counts[tax.classify_swap_shape(tx)] += 1
            d.swap_source_counts[tax.swap_source(tx)] += 1
            if tax.is_multi_hop(tx):
                d.multi_hop_swaps += 1

        for cls in tax.classify_native_transfers(tx):
            d.n_native_transfers += 1
            d.native_class_counts[cls] += 1

        events = translate_helius(tx)
        if not events:
            d.zero_event_txs += 1
        has_trade = False
        for e in events:
            if e.EVENT_TYPE in _TRADE_EVENTS:
                d.trade_events += 1
                has_trade = True
            elif e.EVENT_TYPE == "WalletFunded":
                d.funding_events += 1
        if has_trade and (tx.get("events") or {}).get("swap"):
            d.swaps_with_trade += 1
    return d


def render_markdown(key: str, title: str, method: str, biases: list[str], d: UniverseDistribution) -> str:
    """Render a universe's measured block for ``universes.md`` — consistent across
    runs so universes are directly comparable."""
    def top(counter: Counter, total: int, k: int = 5) -> str:
        return ", ".join(f"{name} {100 * c / total:.1f}%" for name, c in counter.most_common(k)) if total else "—"

    # Surface denominators so low-sample cells are self-evidently uncertain.
    # A rate over fewer than this many events is flagged as low-confidence.
    low_swap = " ⚠" if d.n_parsed_swaps < 100 else ""
    low_nt = " ⚠" if d.n_native_transfers < 100 else ""
    lines = [
        f"### Universe {key} — {title}",
        "",
        f"* **Discovery**: {method}",
        f"* **Sample**: {d.n_transactions} transactions · "
        f"{d.n_parsed_swaps} parsed swaps · {d.n_native_transfers} native transfers",
        f"* **Biases**: {'; '.join(biases)}",
        "",
        "| quantity | value | denominator |",
        "|----------|------:|:--|",
        f"| P(BUG-001 \\| swap) — token-to-token | **{d.p_bug_001:.1%}**{low_swap} | {d.n_parsed_swaps} swaps |",
        f"| P(no trade \\| swap) — swap ignorance | {d.p_swap_untranslated:.1%}{low_swap} | {d.n_parsed_swaps} swaps |",
        f"| P(BUG-002 mechanics \\| transfer) | **{d.p_bug_002_mechanics:.1%}**{low_nt} | {d.n_native_transfers} transfers |",
        f"| funding : trade event ratio | {d.funding_trade_ratio:.1f} : 1 | {d.trade_events} trades |",
        f"| multi-hop rate | {d.multi_hop_rate:.1%}{low_swap} | {d.n_parsed_swaps} swaps |",
        f"| zero-event transactions | {d.p_zero_event_tx:.1%} | {d.n_transactions} txs |",
        "",
        f"* **Top types**: {top(d.type_counts, d.n_transactions)}",
        f"* **Top swap shapes**: {top(d.swap_shape_counts, d.n_parsed_swaps)}",
        f"* **Top sources**: {top(d.swap_source_counts, d.n_parsed_swaps)}",
        "",
    ]
    if low_swap or low_nt:
        lines.append("(⚠ = rate computed over a small denominator — treat as low-confidence.)")
        lines.append("")
    return "\n".join(lines)
