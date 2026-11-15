"""NewSetup backtest package (playbook sections 5.1-5.5).

Event-driven historical replay of layer-1 raw signals through layer-2
confirmation and layer-3 sizing against a broker (injected or built-in
simulator), plus metric computation, hard acceptance gates and a
walk-forward optimizer scaffold.
"""

from __future__ import annotations

import os
import sys

# The sibling `newsetup` (models/config/indicators) and `signals` (layer
# engines) packages live in the NewSetup directory; make sure that directory
# is importable regardless of which sys.path layout the caller used.
_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from .analyzer import BacktestAnalyzer
from .runner import BacktestResult, BacktestRunner, InMemoryPrices
from .walk_forward import WalkForwardOptimizer

__all__ = [
    "BacktestAnalyzer",
    "BacktestResult",
    "BacktestRunner",
    "InMemoryPrices",
    "WalkForwardOptimizer",
]
