# UGT-14 walk-forward tuning evaluation (real data)

## Walk-forward summary (3y train -> 1y test, test years 2020-2024)

- Grid: 1152 combos over the sanctioned space (layer-2 min_score, RSI/SMA windows, ATR SL/TP, heat/sector caps)
- Mean train Sharpe: -0.00 | mean test Sharpe: -0.16
- WFER: 38.08 (meaningful: False; gate >= 0.5: FAIL)
- Final candidate (last fold pick): `{"layer2.min_score": 0.5, "layer2.rsi_period": 7, "layer2.sma_fast": 50, "layer2.sma_slow": 100, "sizing.atr_mult_sl": 3.0, "sizing.reward_risk": 3.0, "risk.max_portfolio_heat_pct": 3.0, "risk.max_sector_exposure_pct": 20.0}`

## A/B on untouched holdout (2025-01-01..2026-11-13)

- Decision: **keep_baseline** (p=1.000, mean diff=0.00, folds=4)

## Tuned playbook windows (acceptance table)

| window | trades | win% | PF | Sharpe | DD% | pass |
|---|---|---|---|---|---|---|
| covid_2020 | 8 | 25.0 | 0.42 | -0.25 | 0.15 | FAIL |
| suez_2021 | 5 | 60.0 | 1.79 | 0.10 | 0.05 | FAIL |
| china_power_2021 | 15 | 26.7 | 0.35 | -0.25 | 0.39 | FAIL |
| russia_sanctions_2022 | 11 | 45.5 | 1.07 | 0.02 | 0.27 | FAIL |
| red_sea_2023_24 | 24 | 16.7 | 0.42 | -0.19 | 0.61 | FAIL |

## Holdout acceptance (2025-01-01..2026-11-13, untouched OOS)

- baseline: trades=112 win=23.2% PF=0.64 Sharpe=-0.19 DD=1.64% -> FAIL
- tuned: trades=68 win=19.1% PF=0.50 Sharpe=-0.17 DD=1.54% -> FAIL

## Structural diagnostics

Layer-2 confirmation tension at raw-signal time (RSI vs SMA support of trigger direction):

- both_agree: 788 (11.0%)
- rsi_only: 1032 (14.4%)
- sma_only: 2542 (35.6%)
- neither: 2787 (39.0%)
- evaluated_signals: 7149

Layer-1 trigger sensitivity (diagnostic only, NOT adopted):

- spike 2.0%/day, 15.0%/30d: 8155 raw signals, trades=196 win=24.5% PF=0.87 Sharpe=-0.04
- spike 1.0%/day, 10.0%/30d: 12219 raw signals, trades=209 win=22.5% PF=0.80 Sharpe=-0.07
- spike 0.75%/day, 8.0%/30d: 13559 raw signals, trades=224 win=25.4% PF=0.94 Sharpe=-0.02

Trigger direction probe (continuation/momentum, diagnostic only):

- default thresholds: 8155 raw signals; trades=158 win=35.4% PF=1.59 Sharpe=0.13 DD=1.12%
- low_threshold thresholds: 13559 raw signals; trades=188 win=36.2% PF=1.58 Sharpe=0.15 DD=1.09%

See wf_evaluation.json for full numbers; tuning detail in wf_tuning.json.
