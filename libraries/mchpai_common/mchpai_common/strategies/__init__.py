"""Trading strategies (canonical, testable). Paper-first by design."""

from .momentum import (
    Features,
    PaperBook,
    Position,
    StrategyParams,
    entry_signal,
    exit_signal,
    position_size,
)
from .execution_model import CostModel, ExecutionModel, Fill

__all__ = [
    "Features",
    "PaperBook",
    "Position",
    "StrategyParams",
    "entry_signal",
    "exit_signal",
    "position_size",
    "CostModel",
    "ExecutionModel",
    "Fill",
]
