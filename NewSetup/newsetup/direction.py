"""Per-inefficiency price-trigger direction policy (UGT-17/19 item 3).

Replaces the hardwired global mean-reversion mapping of layer-1 PRICE
triggers (down-spike -> BUY, up-spike -> SELL) with the data-fitted
per-inefficiency model in config/direction_model.yaml:

  - reversion    : fade the spike (down-spike -> BUY, up-spike -> SELL)
  - continuation : go with the move (down-spike -> SELL, up-spike -> BUY)

Used identically by the live scanner (Layer1Scanner._eval_price) and the
backtest replay (backtest.event_backtests.replay_price_signals) so the
validated stack is the deployed stack.
"""

from __future__ import annotations

from newsetup.config import load_direction_model

REVERSION = "reversion"
CONTINUATION = "continuation"
EVENT = "event"

_policy_cache: dict | None = None


def _policy() -> dict:
    global _policy_cache
    if _policy_cache is None:
        doc = load_direction_model() or {}
        _policy_cache = {
            "default": doc.get("default") or CONTINUATION,
            "inefficiencies": {int(k): v for k, v in
                               (doc.get("inefficiencies") or {}).items()},
        }
    return _policy_cache


def thesis_for(inefficiency_id) -> str:
    """Direction thesis for one inefficiency (model default when unmapped)."""
    pol = _policy()
    entry = pol["inefficiencies"].get(int(inefficiency_id)) if inefficiency_id else None
    if entry and entry.get("direction") in (REVERSION, CONTINUATION):
        return entry["direction"]
    return pol["default"]


def map_direction(thesis: str, move: str) -> str:
    """BUY/SELL for a price move direction under a given thesis."""
    if thesis == REVERSION:
        return "BUY" if move == "DOWN" else "SELL"
    # continuation (and any unknown thesis falls back to the model default
    # semantics: go with the move)
    return "SELL" if move == "DOWN" else "BUY"


def reset_policy_cache() -> None:
    """Test hook: clear the cached direction model."""
    global _policy_cache
    _policy_cache = None
