# UGT-14: Real-data parameter tuning - final report (walk-forward + A/B)

**Verdict: acceptance gates are UNREACHABLE within the sanctioned parameter space on real D1 data.** No parameter combination in the issue-defined search space (layer-2 min_score, RSI/SMA windows, ATR SL/TP multiples, heat/sector caps) passes the playbook 5.3 gates out-of-sample; in fact no combination achieves a meaningfully positive Sharpe even IN-SAMPLE. Per the issue's acceptance option B, this is the structural diagnosis deliverable. **Recommendation: do NOT unblock [UGT-15](/UGT/issues/UGT-15) (Phase-4 paper rollout) on this signal stack; the structural changes in section 5 are prerequisites.**

- Period: 2017-01-01 .. 2026-11-13 (Pepperstone Razor D1 cache, 48 symbols, cached by CTO in `a6713f4`/`619b986`); walk-forward test years 2020-2024, holdout 2025-01-01..2026-11-13 untouched until final evaluation.
- Reproduction: `C:/Python314/python.exe -m backtest.tune_walk_forward tune` then `C:/Python314/python.exe -m backtest.wf_evaluate run` from `NewSetup/`. Full grid = 1152 combos x 5 folds. Tests: 115 passed.
- Verdict commit: `f36d91d` (pipeline + report); numbers in `NewSetup/backtest/results/wf_tuning.json`, `wf_evaluation.json` (gitignored by repo convention, present in workspace), summary in `NewSetup/backtest/results/wf_evaluation.md`.

## 1. Walk-forward grid search (full 1152-combo sanctioned space)

3y train -> 1y test, sliding (test 2020..2024). Per fold, the combo with the best train Sharpe among combos reaching the >=30-trade train floor (680-1152 of 1152 combos eligible per fold):

| test year | best train Sharpe | test Sharpe | test trades | test win% | test PF |
|---|---|---|---|---|---|
| 2020 | -0.09 | -0.41 | 25 | 12.0 | 0.12 |
| 2021 | -0.00 | -0.11 | 35 | 20.0 | 0.68 |
| 2022 | -0.05 | -0.18 | 51 | 21.6 | 0.55 |
| 2023 | +0.04 | -0.14 | 39 | 20.5 | 0.60 |
| 2024 | +0.09 | +0.07 | 34 | 29.4 | 1.38 |

Mean train Sharpe -0.004, mean test Sharpe -0.155. WFER gate: FAIL (train mean <= 0, WFER meaningless). **Key evidence: the best of ALL 1152 combos per fold is at best ~0 in-sample.** A parameter search cannot fix this: there is no edge for it to find.

## 2. A/B on the untouched holdout (2025-01-01..2026-11-13)

Framework: `backtest/ab_testing.py`, 4 folds, adoption strictly per its own rules. Decision: **keep_baseline** (candidate mean fold Sharpe not above baseline; p=1.0). The last-fold candidate (min_score 0.5, RSI 7, SMA 50/100, ATR SL 3.0, RR 3.0, heat 3%, sector 20%) is WORSE than baseline on the holdout:

| variant | trades | win% | PF | Sharpe | DD% | gate |
|---|---|---|---|---|---|---|
| baseline (settings.yaml) | 112 | 23.2 | 0.64 | -0.19 | 1.64 | FAIL |
| tuned (last-fold pick) | 68 | 19.1 | 0.50 | -0.17 | 1.54 | FAIL |

## 3. Playbook windows with tuned candidate (acceptance table)

| window | trades | win% | PF | Sharpe | DD% | pass |
|---|---|---|---|---|---|---|
| covid_2020 | 8 | 25.0 | 0.42 | -0.25 | 0.15 | FAIL |
| suez_2021 | 5 | 60.0 | 1.79 | 0.10 | 0.05 | FAIL (trades << 30) |
| china_power_2021 | 15 | 26.7 | 0.35 | -0.25 | 0.39 | FAIL |
| russia_sanctions_2022 | 11 | 45.5 | 1.07 | 0.02 | 0.27 | FAIL |
| red_sea_2023_24 | 24 | 16.7 | 0.42 | -0.19 | 0.61 | FAIL |

Every window FAILs; every window except red_sea is also below the 30-trade floor. DD is small (<=1.6%) only because layer-3 sizing is very conservative - the risk engine is not the binding constraint; the signal edge is.

## 4. Structural diagnosis (why tuning cannot pass the gates)

1. **EVENT triggers cannot fire on history.** GDELT DOC 2.0 has no historical coverage, so all real-data backtests use layer-1 PRICE-trigger replay only. The engine's core hypothesis - inefficiency-conditioned event responses (UGT-7 cards, keywords) - is therefore UNTESTED on real data; what was tuned is a generic D1 spike-follower, not the playbook design.
2. **Layer-2 confirmation mostly contradicts the trigger.** At raw-signal time (7149 signals evaluated): both RSI and SMA support the trigger direction in only 11.0% of cases; 39.0% support neither. The mean-reversion layer-2 gate (RSI oversold on BUY after a spike UP, plus fast>slow SMA) is internally inconsistent with the layer-1 spike definition for most signals.
3. **Direction mapping is likely wrong.** Diagnostic momentum/continuation probe (same stack, direction follows the move instead of fading it): 8155 raw signals -> PF 1.59, Sharpe 0.13, win 35.4% (low-threshold variant: PF 1.58, Sharpe 0.15), vs the adopted mean-reversion mapping PF 0.78-0.87. Continuation beats reversion by ~2x PF but STILL fails gates (Sharpe ~0.15 vs >=1.0 required) - so flipping direction alone is necessary but not sufficient.
4. **Trade sample is too thin for D1.** Lowering layer-1 thresholds (diagnostic only, outside sanctioned space) raises signals from 8155 -> 13559 but trades only 196 -> 224 and does not improve edge. D1 bars around events give too few, too coarse entries to reach >=30 trades per event window with any quality.
5. **Tuning cannot manufacture edge.** With best-of-grid in-sample Sharpe ~0 across all folds, any gate "pass" achievable by further searching would be overfit noise.

## 5. What would have to change before Phase 4 (recommendations)

1. **Event-conditioned triggers with historical coverage**: ingest a backfillable news/events source (e.g., GDELT hourly archive export, or a vendor with history) so the UGT-7 inefficiency cards actually fire in backtests; or hand-build the 5 playbook event datasets from dated news timelines.
2. **Intraday data (H1/M15) around event windows** so entries/exits resolve within the event response instead of on D1 closes; also raises per-window trade counts toward the 30 floor.
3. **Per-inefficiency direction model**: decide reversion vs continuation per inefficiency type from data (the 4.3 probe suggests continuation dominates for FX spikes), instead of one global mapping.
4. **Re-validate the layer-2 confirmation logic** for internal consistency with layer-1 triggers (the 11%/39% both-agree/neither split).
5. After (1)-(4), rerun this exact walk-forward + holdout pipeline (scripts committed in `f36d91d`) unchanged - it is reusable as-is.

## 6. Limitations

- D1 bars only; intraday dynamics invisible. Pepperstone Razor demo data quality assumed as cached (no independent audit).
- Holdout period 2025-01-01..2026-11-13 includes only ~1.9y and few named "playbook" events; baseline holdout metrics have 112 trades.
- A/B folds report 0 trades in individual folds (sparse events) -> p-value 1.0 is uninformative; decision rests on the full-holdout run.
- Momentum probe is a single-period full-sample diagnostic, NOT a walk-forward-validated variant; it is not adopted and must not be treated as evidence of deployable edge.
