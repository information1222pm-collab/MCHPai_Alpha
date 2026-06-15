"""Canonical NATS subject namespace.

Subjects follow ``mchpai.<domain>.<event>``. JetStream streams bind to wildcard
ranges (``mchpai.tokens.>`` etc.). Keeping subjects centralized means producers
and consumers can never drift out of sync.
"""

PREFIX = "mchpai"

# domains (stream roots)
TOKENS = f"{PREFIX}.tokens"
WALLETS = f"{PREFIX}.wallets"
LIQUIDITY = f"{PREFIX}.liquidity"
SIGNALS = f"{PREFIX}.signals"
EXEC = f"{PREFIX}.exec"

# concrete subjects
TOKEN_CREATED = f"{TOKENS}.created"
TOKEN_SNAPSHOT = f"{TOKENS}.snapshot"

WALLET_CREATED = f"{WALLETS}.created"
WALLET_UPDATED = f"{WALLETS}.updated"
WALLET_BOUGHT = f"{WALLETS}.bought"
WALLET_SOLD = f"{WALLETS}.sold"

LIQUIDITY_ADDED = f"{LIQUIDITY}.added"
LIQUIDITY_REMOVED = f"{LIQUIDITY}.removed"

ATTENTION_SPIKE = f"{SIGNALS}.attention_spike"
CLUSTER_DETECTED = f"{SIGNALS}.cluster_detected"
PREDICTION_GENERATED = f"{SIGNALS}.prediction"
BUY_SIGNAL = f"{SIGNALS}.buy_signal"

ORDER_REQUESTED = f"{EXEC}.order"
TRADE_EXECUTED = f"{EXEC}.trade_executed"
FILL = f"{EXEC}.fill"

# stream definitions: name -> subject wildcard
STREAMS = {
    "TOKENS": f"{TOKENS}.>",
    "WALLETS": f"{WALLETS}.>",
    "LIQUIDITY": f"{LIQUIDITY}.>",
    "SIGNALS": f"{SIGNALS}.>",
    "EXEC": f"{EXEC}.>",
}
