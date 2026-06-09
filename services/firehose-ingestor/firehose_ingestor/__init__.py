"""MCHPAI firehose-ingestor — full-coverage server-side Alpha engine.

The dashboard's intelligence (wallet grading, Alpha Score, signal feed) fed by
the complete DEX firehose instead of a browser poll sample. Engine and mock
transport are pure Python (offline-testable); the WebSocket/gRPC transports and
the FastAPI server are lazy-imported deploy dependencies.
"""

from .engine import AlphaEngine
from .transport import Firehose, MockFirehose, HeliusWsFirehose, YellowstoneFirehose
from .rpc import ctx_from_jsonparsed, swaps_from_jsonparsed

__all__ = [
    "AlphaEngine", "Firehose", "MockFirehose", "HeliusWsFirehose",
    "YellowstoneFirehose", "ctx_from_jsonparsed", "swaps_from_jsonparsed",
]
