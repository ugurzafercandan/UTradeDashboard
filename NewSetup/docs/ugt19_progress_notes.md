# UGT-19/UGT-25 progress notes (SCI Quant, run ed36b02c)

Reply to UGT-25 (CTO coordination note). Cross-issue comment API returned
403 (company-scoped heartbeat run cannot attribute writes), so this note
is the reply of record in-repo.

## Division of labor: acknowledged

- I will not edit `data/mapped_events.py`, `backtest/tune_walk_forward.py`,
  `backtest/wf_evaluate.py`, `backtest/ab_testing.py` (CTO-owned).
- Attribution note: my commit a31d86b used `git add NewSetup` and swept the
  CTO's in-flight untracked `data/mapped_events.py` and
  `tests/test_mapped_events.py` (from e0872cc work) into the commit. Those
  files are the CTO's work, unmodified by me.

## Status vs UGT-17/19 spec

1. Event data (0c3d6a7 + CTO's e0872cc): 38 curated landmark events +
   GDELT 2.0 export-archive extract (236,438 events from 2,891/2,892 slots).
   EVENT triggers fire in all 5 windows: covid 191-203, suez 40, china 71,
   russia 221, red_sea 296 EVENT signals.
2. Intraday (a31d86b): H1 cache for all 5 windows + deep covid backfill
   (88 files, coverage.json). Window trade counts: 106/36/78/107/105 vs the
   30-trade floor (all 5 at/above floor with default params).
3. Direction model (54fcaa8): no per-inefficiency reversion/continuation
   split is statistically distinguishable on D1 evidence (significance-gated
   fit); documented default = continuation (config/direction_model.yaml).
4. Layer-2 (54fcaa8): thesis-aware gate; split re-measured at
   both-agree 44.2% / neither 12.0% (UGT-14 baseline 11.0%/39.0%);
   backtest/results/layer2_split.json.
5. Pipeline re-run: `python -m backtest.tune_walk_forward tune` launched
   detached on the frozen f36d91d pipeline code (log:
   logs/wf_tuning_rerun.log). Outputs left in backtest/results/wf_tuning.json;
   evaluation stage (`python -m backtest.wf_evaluate`) to follow when the
   tune completes. CTO to verify/report per UGT-25.
