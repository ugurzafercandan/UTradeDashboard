"""Forex strategy layer (playbook Appendix B).

Loads the 6 config-driven FX strategy definitions (FX-1..FX-6) from
config/fx_strategies.yaml and evaluates their entry conditions against a
supplied market/regime context. Entry conditions are declarative:

    {"all":      [leaf, ...]}            every leaf must hold
    {"any":      [leaf, ...]}            at least one leaf must hold
    {"majority": {"conditions": [...],   at least ``min_required`` leaves
                 "min_required": n}}     must hold
    leaf = {"metric": "rsi.AUDUSD", "op": "<", "value": 45}

A strategy has one or more named entry variants (e.g. FX-2's ``fast`` and
``confirmed``); the strategy fires if any variant's groups all pass, and
then each instrument's own entry condition (if any) is checked to decide
which pairs are eligible.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from newsetup.config import load_fx_strategies

_OPS = {
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


@dataclass
class FXInstrument:
    symbol: str
    direction: str
    rationale: str = ""
    risk_pct: float | None = None
    entry: dict | None = None          # optional leaf condition on a metric
    severe_only: bool = False          # FX-3 AUDJPY: only on severe crisis
    stop_pips: int | None = None
    take_profit_pips: int | None = None


@dataclass
class FXStrategy:
    id: str
    name: str
    description: str
    trigger: str
    avg_duration_days: list[int]
    expected_frequency: str
    instruments: list[FXInstrument] = field(default_factory=list)
    scenarios: list[dict] = field(default_factory=list)   # FX-5 event scenarios
    entry_variants: dict[str, list] = field(default_factory=dict)
    position_sizing: dict = field(default_factory=dict)
    exit_rules: list[str] = field(default_factory=list)

    def symbols(self) -> list[str]:
        return [i.symbol for i in self.instruments] + \
               [s["symbol"] for s in self.scenarios]


def _strategy_from_raw(raw: dict) -> FXStrategy:
    instruments = [
        FXInstrument(
            symbol=i["symbol"],
            direction=i["direction"],
            rationale=i.get("rationale", ""),
            risk_pct=i.get("risk_pct"),
            entry=i.get("entry"),
            severe_only=bool(i.get("severe_only", False)),
            stop_pips=i.get("stop_pips"),
            take_profit_pips=i.get("take_profit_pips"),
        )
        for i in raw.get("instruments", [])
    ]
    return FXStrategy(
        id=raw["id"],
        name=raw["name"],
        description=raw.get("description", ""),
        trigger=raw.get("trigger", ""),
        avg_duration_days=raw.get("avg_duration_days", []),
        expected_frequency=raw.get("expected_frequency", ""),
        instruments=instruments,
        scenarios=raw.get("scenarios", []),
        entry_variants=raw.get("entry_variants", {}),
        position_sizing=raw.get("position_sizing", {}),
        exit_rules=raw.get("exit_rules", []),
    )


def load_strategies() -> list[FXStrategy]:
    """All 6 FX strategies as domain objects."""
    return [_strategy_from_raw(s) for s in load_fx_strategies()]


def get_strategy(strategy_id: str) -> FXStrategy:
    for s in load_strategies():
        if s.id == strategy_id:
            return s
    raise KeyError(f"unknown FX strategy {strategy_id}")


# ------------------------------------------------------------------ checks
def _check_leaf(cond: dict, context: dict) -> tuple[bool, str]:
    metric, op, value = cond["metric"], cond.get("op", "=="), cond["value"]
    actual = context.get(metric)
    if actual is None:
        return False, f"{metric} missing (need {op} {value})"
    fn = _OPS.get(op)
    if fn is None:
        return False, f"unsupported operator {op}"
    ok = fn(actual, value)
    return ok, f"{metric}={actual} {op} {value} -> {'PASS' if ok else 'FAIL'}"


def _eval_group(group: dict, context: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if "all" in group:
        ok = True
        for cond in group["all"]:
            passed, why = _check_leaf(cond, context)
            ok = ok and passed
            reasons.append(why)
        return ok, reasons
    if "any" in group:
        results = [_check_leaf(cond, context) for cond in group["any"]]
        reasons.extend(why for _, why in results)
        return any(p for p, _ in results), reasons
    if "majority" in group:
        block = group["majority"]
        results = [_check_leaf(cond, context) for cond in block["conditions"]]
        reasons.extend(why for _, why in results)
        passed = sum(1 for p, _ in results if p)
        return passed >= block["min_required"], reasons
    return False, [f"malformed condition group: {group}"]


def _eval_variant(groups: list[dict], context: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    for group in groups:
        ok, why = _eval_group(group, context)
        reasons.extend(why)
        if not ok:
            return False, reasons
    return True, reasons


def evaluate_entry(strategy: FXStrategy, context: dict,
                   severe_crisis: bool = False) -> dict:
    """Evaluate a strategy against a market/regime context.

    ``context`` maps metric names (``rsi.AUDUSD``, ``gdelt.…``, ``vix.level``)
    to current values. Returns::

        {"eligible": bool, "variant": str|None, "reasons": [str],
         "eligible_instruments": [FXInstrument]}

    ``severe_crisis`` gates instruments flagged ``severe_only`` (FX-3 AUDJPY).
    """
    eligible_variant: str | None = None
    all_reasons: list[str] = []
    for variant, groups in strategy.entry_variants.items():
        ok, reasons = _eval_variant(groups, context)
        all_reasons.extend(f"[{variant}] {r}" for r in reasons)
        if ok:
            eligible_variant = variant
            break
    if eligible_variant is None:
        return {"eligible": False, "variant": None, "reasons": all_reasons,
                "eligible_instruments": []}

    eligible_instruments: list[FXInstrument] = []
    for inst in strategy.instruments:
        if inst.severe_only and not severe_crisis:
            all_reasons.append(f"{inst.symbol}: severe_only, not a severe crisis -> skip")
            continue
        if inst.entry is None:
            eligible_instruments.append(inst)
            continue
        passed, why = _check_leaf(inst.entry, context)
        all_reasons.append(f"[{inst.symbol}] {why}")
        if passed:
            eligible_instruments.append(inst)
    return {"eligible": True, "variant": eligible_variant,
            "reasons": all_reasons,
            "eligible_instruments": eligible_instruments}
