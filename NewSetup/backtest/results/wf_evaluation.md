# UGT-14 walk-forward tuning evaluation (real data)

## Walk-forward summary (3y train -> 1y test, test years 2020-2024)

- Grid: 1152 combos over the sanctioned space (layer-2 min_score, RSI/SMA windows, ATR SL/TP, heat/sector caps)
- Mean train Sharpe: 1.28 | mean test Sharpe: 0.96
- WFER: 0.75 (meaningful: True; gate >= 0.5: PASS)
- Final candidate (last fold pick): `{"layer2.min_score": 0.35, "layer2.rsi_period": 7, "layer2.sma_fast": 50, "layer2.sma_slow": 100, "sizing.atr_mult_sl": 1.5, "sizing.reward_risk": 1.0, "risk.max_portfolio_heat_pct": 3.0, "risk.max_sector_exposure_pct": 20.0}`

## A/B on untouched holdout (2025-01-01..2026-11-13)

- Decision: **keep_baseline** (p=1.000, mean diff=0.00, folds=4)

## Tuned playbook windows (acceptance table)

| window | trades | win% | PF | Sharpe | DD% | pass |
|---|---|---|---|---|---|---|
| covid_2020 | 250 | 54.4 | 1.15 | 0.05 | 0.91 | FAIL |
| suez_2021 | 80 | 71.2 | 2.34 | 0.16 | 0.25 | FAIL |
| china_power_2021 | 168 | 66.1 | 1.95 | 0.16 | 0.24 | FAIL |
| russia_sanctions_2022 | 191 | 57.1 | 1.29 | 0.07 | 0.60 | FAIL |
| red_sea_2023_24 | 205 | 56.1 | 1.21 | 0.06 | 0.64 | FAIL |

## Holdout acceptance (2025-01-01..2026-11-13, untouched OOS)

- baseline: trades=178 win=47.2% PF=1.66 Sharpe=0.26 DD=0.82% -> FAIL
- tuned: trades=667 win=78.6% PF=3.57 Sharpe=1.22 DD=0.25% -> PASS

## Structural diagnostics

Layer-2 confirmation tension at raw-signal time (thesis-aware gate, both components supporting the trigger):

- both_agree: 3588 (44.5%)
- rsi_only: 2378 (29.5%)
- sma_only: 1144 (14.2%)
- neither: 952 (11.8%)
- evaluated signals: 8062
- old one-size gate on the same signals: both_agree 134 (1.7%), rsi_only 168 (2.1%), sma_only 4166 (51.7%), neither 3594 (44.6%)
- thesis=continuation: 7149 signals, both-agree 39.6%, neither 13.3%
- thesis=event: 913 signals, both-agree 83.2%, neither 0.0%

Layer-1 trigger sensitivity (diagnostic only, NOT adopted):

- spike 2.0%/day, 15.0%/30d: 8155 raw signals, trades=2547 win=78.8% PF=3.61 Sharpe=1.52
- spike 1.0%/day, 10.0%/30d: 12219 raw signals, trades=2572 win=73.1% PF=2.63 Sharpe=1.22
- spike 0.75%/day, 8.0%/30d: 13559 raw signals, trades=2640 win=70.7% PF=2.31 Sharpe=1.10

Trigger direction probe (continuation/momentum, diagnostic only):

- default thresholds: 8155 raw signals; trades=2547 win=78.8% PF=3.61 Sharpe=1.52 DD=0.35%
- low_threshold thresholds: 13559 raw signals; trades=2640 win=70.7% PF=2.31 Sharpe=1.10 DD=0.45%

See wf_evaluation.json for full numbers; tuning detail in wf_tuning.json.
