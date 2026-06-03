"""Timeline engines — incremental reducers that emit ``state(t)``.

Each reducer ingests events in order and, after each one, can emit the entity's
current state. Storing these emissions append-only gives a full *trajectory* per
wallet / creator / graph — the substrate for wallet transformers, creator
embeddings, and temporal GNNs.

Reducers are pure (no I/O), so they are trivially unit-tested and can be replayed
deterministically over historical events to rebuild any state(t).
"""

from .wallet_state import WalletStateReducer
from .creator_state import CreatorStateReducer
from .graph_state import GraphStateReducer
from .trajectory import build_trajectory

__all__ = [
    "WalletStateReducer",
    "CreatorStateReducer",
    "GraphStateReducer",
    "build_trajectory",
]
