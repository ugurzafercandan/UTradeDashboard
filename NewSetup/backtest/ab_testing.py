"""A/B testing framework scaffold for candidate signal variants
(playbook 9.5).

Compares a baseline parameter set against a candidate variant on the
SAME data: a full-run comparison plus a paired per-fold comparison.

Design (stated honestly):
- The timeline is split into ``folds`` contiguous chunks; both variants
  run over every fold, and the per-fold Sharpe difference
  (candidate - baseline) forms a paired sample.
- Significance is a paired t-statistic with a normal-approximation
  two-sided p-value (erf-based; no scipy dependency). With folds < 5
  this approximation is crude — treat the p-value as advisory only.
- Decision rules:
    * fewer than ``min_folds`` usable folds or fewer trades than the
      acceptance minimum in either full run -> "inconclusive";
    * mean paired diff > 0 and p < p_value_threshold -> "adopt_candidate";
    * otherwise -> "keep_baseline".
- A/B results on SYNTHETIC data validate plumbing only; adoption for
  live trading additionally requires the winner to pass the 5.3
  acceptance gate and 5.5 walk-forward on out-of-sample REAL data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from newsetup.config import load_settings
from newsetup.models import PriceBar, RawSignal

from .runner import BacktestRunner
from .walk_forward import _merged_timeline, _slice_window


@dataclass
class ABVariant:
    """One named parameter set (settings_overrides for BacktestRunner)."""

    name: str
    settings_overrides: dict = field(default_factory=dict)


@dataclass
class ABTestResult:
    """Outcome of one baseline-vs-candidate comparison."""

    baseline: str
    candidate: str
    baseline_metrics: dict = field(default_factory=dict)
    candidate_metrics: dict = field(default_factory=dict)
    fold_sharpes: list[dict] = field(default_factory=list)   # per-fold pairs
    mean_diff: float = 0.0
    t_stat: float = 0.0
    p_value: float = 1.0
    folds: int = 0
    decision: str = "inconclusive"   # adopt_candidate | keep_baseline | inconclusive
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "baseline": self.baseline,
            "candidate": self.candidate,
            "baseline_metrics": self.baseline_metrics,
            "candidate_metrics": self.candidate_metrics,
            "fold_sharpes": self.fold_sharpes,
            "mean_diff": self.mean_diff,
            "t_stat": self.t_stat,
            "p_value": self.p_value,
            "folds": self.folds,
            "decision": self.decision,
            "notes": self.notes,
        }


def _paired_ttest(diffs: list[float]) -> tuple[float, float]:
    """Paired t-statistic and two-sided normal-approximation p-value."""
    n = len(diffs)
    if n < 2:
        return 0.0, 1.0
    mean = sum(diffs) / n
    var = sum((d - mean) ** 2 for d in diffs) / (n - 1)
    std = math.sqrt(var)
    if std == 0.0:
        if mean == 0.0:
            return 0.0, 1.0
        return (math.inf if mean > 0 else -math.inf), 0.0
    t = mean / (std / math.sqrt(n))
    # Normal approximation of the two-sided p-value.
    z = abs(t)
    p = math.erfc(z / math.sqrt(2.0))  # erfc is exact 2*(1-Phi(z))
    return t, p


class ABTestFramework:
    """Runs paired variant comparisons over shared data (playbook 9.5)."""

    def __init__(self, runner: BacktestRunner, settings: Optional[dict] = None):
        self.runner = runner
        self.settings = settings or runner.settings or load_settings()
        ab = self.settings.get("ab_testing", {}) or {}
        self.min_folds = int(ab.get("min_folds", 3))
        self.p_threshold = float(ab.get("p_value_threshold", 0.05))
        acc = self.settings.get("backtest", {}).get("acceptance", {}) or {}
        self.min_trades = int(acc.get("min_trades", 30))

    # ------------------------------------------------------------------ run
    def compare(self,
                baseline: ABVariant,
                candidate: ABVariant,
                price_data: dict[str, list[PriceBar]],
                raw_signals: list[RawSignal],
                folds: int = 4) -> ABTestResult:
        """Full-run + paired per-fold comparison of the two variants."""
        result = ABTestResult(baseline=baseline.name, candidate=candidate.name)

        full_base = self.runner.run(price_data, raw_signals,
                                     settings_overrides=baseline.settings_overrides)
        full_cand = self.runner.run(price_data, raw_signals,
                                    settings_overrides=candidate.settings_overrides)
        result.baseline_metrics = full_base.metrics
        result.candidate_metrics = full_cand.metrics

        events = _merged_timeline(price_data)
        if not events or folds < 1:
            result.notes.append("no timeline events or folds < 1")
            return result

        # Contiguous fold boundaries over the merged timeline.
        fold_size = len(events) // folds
        usable = 0
        for k in range(folds):
            lo = k * fold_size
            hi = (k + 1) * fold_size if k < folds - 1 else len(events)
            fold_events = events[lo:hi]
            fold_data, fold_signals = _slice_window(price_data, fold_events,
                                                    raw_signals)
            if not fold_data:
                continue
            base = self.runner.run(fold_data, fold_signals,
                                   settings_overrides=baseline.settings_overrides)
            cand = self.runner.run(fold_data, fold_signals,
                                   settings_overrides=candidate.settings_overrides)
            result.fold_sharpes.append({
                "fold": k,
                "baseline_sharpe": base.metrics.get("sharpe", 0.0),
                "candidate_sharpe": cand.metrics.get("sharpe", 0.0),
                "baseline_trades": base.metrics.get("total_trades", 0),
                "candidate_trades": cand.metrics.get("total_trades", 0),
            })
            usable += 1

        result.folds = usable
        diffs = [f["candidate_sharpe"] - f["baseline_sharpe"]
                 for f in result.fold_sharpes]
        result.mean_diff = sum(diffs) / len(diffs) if diffs else 0.0
        result.t_stat, result.p_value = _paired_ttest(diffs)

        base_trades = result.baseline_metrics.get("total_trades", 0)
        cand_trades = result.candidate_metrics.get("total_trades", 0)
        if usable < self.min_folds:
            result.decision = "inconclusive"
            result.notes.append(
                f"only {usable} usable folds (< {self.min_folds}); "
                "not enough paired evidence")
        elif base_trades < self.min_trades or cand_trades < self.min_trades:
            result.decision = "inconclusive"
            result.notes.append(
                f"trade counts baseline={base_trades}, candidate={cand_trades}; "
                f"below acceptance minimum {self.min_trades}")
        elif result.mean_diff > 0.0 and result.p_value < self.p_threshold:
            result.decision = "adopt_candidate"
        else:
            result.decision = "keep_baseline"
            if result.mean_diff <= 0.0:
                result.notes.append("candidate mean fold Sharpe not above baseline")
        return result
