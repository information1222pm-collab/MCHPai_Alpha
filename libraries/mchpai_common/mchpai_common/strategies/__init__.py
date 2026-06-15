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
from .rl_policy import OnlineBandit

__all__ = [
    "OnlineBandit",
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
