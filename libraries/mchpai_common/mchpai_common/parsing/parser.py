"""The universal swap parser.

Given a normalized :class:`TxContext` (the fields any RPC/Geyser tx meta provides
— pre/post SOL lamports and pre/post token balances per owner, plus invoked
program ids), produce zero or more :class:`SwapEvent`.

We reconstruct each trader's economic position change from balance deltas:

    buy:  SOL decreases, token increases
    sell: SOL increases, token decreases

SOL movement = native lamport delta + WSOL token delta (wrapped SOL), with the
fee added back for the fee payer so gas never pollutes trade size. The trader is
the fee payer (and any caller-supplied additional signers); pool/vault accounts
are never emitted because we only consider trader-owned balances.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..schemas.common import Side
from ..schemas.swap import Dex, SwapEvent
from .program_ids import WSOL_MINT, detect_dex

LAMPORTS_PER_SOL = 1_000_000_000


@dataclass
class TokenBalance:
    owner: str
    mint: str
    amount: float          # UI amount (decimal-adjusted)


@dataclass
class TxContext:
    signature: str
    slot: int
    timestamp: datetime
    fee_payer: str
    program_ids: list[str]
    pre_sol_lamports: dict[str, int]      # account/owner -> lamports
    post_sol_lamports: dict[str, int]
    pre_token_balances: list[TokenBalance]
    post_token_balances: list[TokenBalance]
    fee_lamports: int = 0
    # marketcap support: circulating supply (UI units) per mint, if known
    supply: dict[str, float] = field(default_factory=dict)
    # additional trader owners beyond the fee payer (e.g. multi-signer bundles)
    extra_traders: list[str] = field(default_factory=list)


def _token_delta_by_owner(ctx: TxContext) -> dict[tuple[str, str], float]:
    deltas: dict[tuple[str, str], float] = {}
    for tb in ctx.pre_token_balances:
        deltas[(tb.owner, tb.mint)] = deltas.get((tb.owner, tb.mint), 0.0) - tb.amount
    for tb in ctx.post_token_balances:
        deltas[(tb.owner, tb.mint)] = deltas.get((tb.owner, tb.mint), 0.0) + tb.amount
    return deltas


def _native_sol_delta(ctx: TxContext, owner: str) -> float:
    pre = ctx.pre_sol_lamports.get(owner, 0)
    post = ctx.post_sol_lamports.get(owner, 0)
    lamports = post - pre
    if owner == ctx.fee_payer:
        lamports += ctx.fee_lamports  # exclude gas from trade size
    return lamports / LAMPORTS_PER_SOL


class UniversalSwapParser:
    def parse(self, ctx: TxContext) -> list[SwapEvent]:
        dex = detect_dex(ctx.program_ids)
        if dex is Dex.unknown:
            return []

        token_deltas = _token_delta_by_owner(ctx)
        traders = [ctx.fee_payer, *ctx.extra_traders]
        events: list[SwapEvent] = []

        for owner in traders:
            # WSOL delta counts as SOL movement, not a token leg.
            wsol_delta = token_deltas.get((owner, WSOL_MINT), 0.0)
            sol_delta = _native_sol_delta(ctx, owner) + wsol_delta

            # primary token leg = largest |delta| among this owner's non-WSOL mints
            legs = [
                (mint, d)
                for (o, mint), d in token_deltas.items()
                if o == owner and mint != WSOL_MINT and abs(d) > 0
            ]
            if not legs:
                continue
            mint, tok_delta = max(legs, key=lambda kv: abs(kv[1]))

            # a real swap has opposite-signed SOL and token movement
            if tok_delta > 0 and sol_delta < 0:
                side = Side.buy
            elif tok_delta < 0 and sol_delta > 0:
                side = Side.sell
            else:
                continue

            sol_amount = abs(sol_delta)
            token_amount = abs(tok_delta)
            price = sol_amount / token_amount if token_amount > 0 else None
            mcap = None
            if price is not None and mint in ctx.supply:
                mcap = price * ctx.supply[mint]

            events.append(
                SwapEvent(
                    signature=ctx.signature,
                    slot=ctx.slot,
                    timestamp=ctx.timestamp,
                    dex=dex,
                    wallet_address=owner,
                    token_address=mint,
                    side=side,
                    sol_amount=sol_amount,
                    token_amount=token_amount,
                    price=price,
                    market_cap=mcap,
                    program_id=next(iter(ctx.program_ids), None),
                )
            )
        return events


_DEFAULT = UniversalSwapParser()


def parse_transaction(ctx: TxContext) -> list[SwapEvent]:
    """Module-level convenience wrapper around the default parser."""
    return _DEFAULT.parse(ctx)
