# UGT-19 structural rework report (SCI Quant; status: items 1-4 complete, item 5 pipeline re-run executed per UGT-25 division of labor)

Run: ed36b02c (SCI Quant heartbeat). Spec: UGT-17 (= UGT-14 sec 5) reproduced
in UGT-19. Coordination: UGT-25 - CTO adopted items 1/3/4 (commits 0c3d6a7,
54fcaa8), supplied the 101-event dataset (e0872cc) and owns the final
pipeline re-run + report; item 2 intraday rework is mine (a31d86b).

## Item 1 - Backfillable historical event data

- config/event_history.yaml: 38 curated dated landmark events across the 5
  playbook windows, each with source URL, goldstein score, relevance score.
- GDELT 2.0 export archive extract: scripts/fetch_gdelt_window_exports.py
  downloaded 2,891/2,892 planned 15-minute slots (6/day over every window
  day; 1 slot failed after retries - noted limitation), filtered to
  disruptive events (Goldstein <= -5 with >= 5 articles, or material-conflict
  CAMEO root codes 18/19/20 with >= 10 articles, or mass protest <= -4 with
  >= 50 articles): 236,438 events in data/caches/events/gdelt_export_events.csv.
- data/historical_events.py: event store + EventProvider + replay matcher
  mirroring Layer1Scanner._eval_event (keywords, score gate, direction
  heuristic).
- Layer-1 consistency fix (scanner + replay kept identical): the keyword
  shock vocabulary now equals the _is_supply_shock direction vocabulary;
  previously war/attack/halt could set direction but could never fire a
  trigger.

EVENT triggers fire in all 5 windows (raw signal counts per window):

| window | events in window | EVENT signals | PRICE signals |
|---|---|---|---|
| covid_2020 | 70,094 | 191-203 | 98-171 |
| suez_2021 | 19,962 | 40 | 63-64 |
| china_power_2021 | 32,477 | 71 | 133-157 |
| russia_sanctions_2022 | 33,650 | 221 | 155-226 |
| red_sea_2023_24 | 77,826 | 296 | 278-383 |

(Ranges reflect D1-only vs intraday replay variants.)

## Item 2 - Intraday data (H1/M15)

- H1 bars per symbol for all 5 playbook windows (240d warmup) plus a deep
  2018-06 backfill for the covid window: 88 files in data/caches/intraday/.
  M15 fetched for the red_sea window (Pepperstone M15 depth starts 2022-08).
  coverage.json reports per symbol/window usability.
- Broker depth limitations (honest): Pepperstone demo H1 starts 2018-06
  (FX/metals), equities/ETF CFDs start 2020-06, Aluminium H1 only from
  2023-07; covid window intraday usable for 21 of 48 symbols, later
  windows 36-40 of 48. 5 symbols have no broker mapping at all.
- Runner multi-timeframe rework: execution stream (H1) for entries/exits
  and ATR stop sizing; layer-2 RSI/SMA stay on daily aggregates of the
  H1 stream (playbook daily semantics preserved).
- Window trade counts vs the 30-trade floor (default settings, rebuilt
  stack): covid 106, suez 36, china 78, russia 107, red_sea 105 (was
  27/10/25/24/31 on the old D1 stack). All 5 windows at/above the floor.
- Tradeoffs: with execution-timeframe ATR stops, win rates at default
  params run 37-45% (below the 48% gate) and PF 1.11-1.58; with
  daily-ATR stops win rates were 48-70% and PF 1.9-3.2 but trades 10-31
  (below floor) with 80-day holds. The walk-forward grid tunes
  atr_mult_sl/reward_risk on the rebuilt stack.

## Item 3 - Per-inefficiency direction model

- scripts/fit_direction_model.py: per-inefficiency reversion vs
  continuation from 5,325 layer-1 PRICE trigger moments on D1 history
  (10-trading-day forward returns), fit window ends 2024-12-31 so the
  untouched holdout stays clean.
- Result (honest): NO inefficiency's reversion/continuation split is
  statistically distinguishable. Global continuation expectancy
  -0.024% +/- 0.109% SE (PF 0.99 vs 1.01) - the 1.645*SE significance
  gate rejects per-inefficiency and category decisions; all 40 resolve
  to the documented global default: continuation (consistent with the
  UGT-14 continuation probe PF 1.59 through the stack).
- Per-inefficiency stats recorded in config/direction_model.yaml;
  newsetup/direction.py policy wired identically into the live scanner
  and the backtest replay (validated stack == live stack).

## Item 4 - Layer-1/layer-2 consistency rework

- Layer2Confirmation rewritten thesis-aware (reversion / continuation /
  event), replacing the old one-size gate that required a reversion
  signal to pass continuation checks (the source of the 11%/39% split).
- Re-measured (scripts/measure_layer2_split.py, 7,952 raw signals, 7,149
  PRICE + 803 EVENT):
  - both-agree: 11.0% -> 44.2% (EVENT triggers: 85.2%)
  - neither:    39.0% -> 12.0%
  - old-gate split on the same new signals: 1.6% both / 44.6% neither.
- Full backtest/results/layer2_split.json.

## Item 5 - Pipeline re-run (frozen f36d91d code on the rebuilt stack)

- My tune run (logs/wf_tuning_rerun.log) completed folds 1-2 before being
  killed by a session-kernel timeout: fold 2020 train Sharpe 1.47 / test
  Sharpe 1.10 (211 trades), fold 2021 train 1.43 / test 1.27 (345 trades)
  - vs UGT-14's ~0 train / -0.155 mean test.
- Per UGT-25 the CTO owns the final tune_walk_forward + wf_evaluate runs;
  their tune (launched 22:24 local, frozen f36d91d pipeline + adopted
  stack + their event conditioning, commit f5ffc57) completed and the
  evaluation stage ran to completion. Numbers below are from
  backtest/results/wf_tuning.json + wf_evaluation.json (generated
  2026-11-16T06:53Z / 06:59Z).

### Final pipeline results (rebuilt stack)

Walk-forward (3y train -> 1y test, 1152-combo grid, test years 2020-2024):

| fold | train Sharpe | test Sharpe | test trades | test win% | test PF | test DD% |
|---|---|---|---|---|---|---|
| 2020 | 1.260 | 0.856 | 217 | 74.2 | 2.77 | 0.19 |
| 2021 | 1.180 | 1.279 | 349 | 79.4 | 3.88 | 0.32 |
| 2022 | 1.393 | 0.680 | 317 | 68.5 | 2.15 | 0.51 |
| 2023 | 1.252 | 1.046 | 349 | 76.8 | 3.33 | 0.29 |
| 2024 | 1.313 | 0.929 | 340 | 77.4 | 3.41 | 0.29 |

- Mean train Sharpe 1.279, mean test Sharpe 0.958 (UGT-14: ~0 / -0.155).
- WFER 0.749 >= 0.5 gate: PASS (meaningful, train > 0).

Untouched holdout acceptance (2025-01-01..2026-11-13):

| variant | trades | win% | PF | Sharpe | maxDD% | verdict |
|---|---|---|---|---|---|---|
| baseline | 178 | 47.2 | 1.66 | 0.26 | 0.82 | FAIL (win, Sharpe) |
| tuned | 667 | 78.6 | 3.57 | 1.22 | 0.25 | **ALL GATES PASS** |

Tuned playbook windows (with intraday execution):

| window | trades | win% | PF | Sharpe | DD% | verdict |
|---|---|---|---|---|---|---|
| covid_2020 | 250 | 54.4 | 1.15 | 0.05 | 0.91 | FAIL (PF, Sharpe) |
| suez_2021 | 80 | 71.2 | 2.34 | 0.16 | 0.25 | FAIL (Sharpe) |
| china_power_2021 | 168 | 66.1 | 1.95 | 0.16 | 0.24 | FAIL (Sharpe) |
| russia_sanctions_2022 | 191 | 57.1 | 1.29 | 0.07 | 0.60 | FAIL (PF marginal 1.29, Sharpe) |
| red_sea_2023_24 | 205 | 56.1 | 1.21 | 0.06 | 0.64 | FAIL (PF, Sharpe) |

- Direction probe (continuation, full period): PF 3.61, Sharpe 1.52.
- Confirmation tension on the rebuilt stack: both-agree 44.5%, neither
  11.8% (old-gate split on same signals: 1.7%/44.6%).

### Honest verdict and open items

1. Holdout OOS acceptance PASSES every gate with the tuned candidate
   (Sharpe 1.22 >= 1.0, DD 0.25% <= 12%, win 78.6% >= 48%, PF 3.57 >= 1.3,
   667 >= 30 trades), and WFER 0.749 >= 0.5. The structural rework moved
   the stack from "no edge for tuning to find" (UGT-14) to a walk-forward
   + holdout-passing configuration.
2. Per-window acceptance still FAILS on per-window Sharpe (0.05-0.16) and
   marginally on PF in 3 windows - single 4-5-month windows with
   conservative per-trade risk (0.5%, min-lot floored) produce ~1%
   window returns; Sharpe at that scale is structurally low. This is a
   measurement-scale artifact as much as an edge deficiency; it should
   be the next binding constraint to address (window-relative risk sizing
   or per-window Sharpe convention), NOT papered over.
3. ANOMALY to verify before any rollout decision: the A/B test on the
   holdout returned decision keep_baseline with p=1.0 and mean_diff=0.0,
   while the same holdout shows baseline FAIL vs tuned PASS on every
   metric. p=1.0/diff=0.0 indicates the A/B compared two identical
   variants (likely the tuned overrides not reaching the A/B runner in
   the integrated event-conditioning version). The holdout acceptance
   table is the trustworthy signal; the A/B needs a fix + re-run before
   it is cited either way.
4. Caveats for the adoption decision: the event store windows + CTO's
   101-event dataset are hand-curated/GDELT-derived news timelines (news
   hours approximate); intraday depth limits as listed above; the tuned
   candidate (min_score 0.35, RSI 7, SMA 50/100, atr_mult 1.5, RR 1.0,
   heat 3%, sector 20%) is selected on folds ending 2024 and verified
   only on the 2025-2026 holdout - UGT-15 paper trading remains the
   required next gate before any live exposure.

## Data limitations (summary)

- GDELT export slot 20231111184500 failed all retries (1 of 2,892).
- Intraday H1 depth per class of instrument as above; M15 only red_sea;
  intraday bar timestamps are terminal server time vs event UTC (<=3h
  skew, immaterial at H1 resolution given news-date granularity).
- Intraday CSV volume column is 0 (volume lost in a fetch-script bug that
  shifted columns; OHLC recovered; volume unused by layers 2-3).
- Event store covers the 5 playbook windows only; walk-forward fold years
  outside the windows still replay PRICE triggers only (per the frozen
  pipeline design; the CTO's 101-event dataset extends 2017-2026 coverage
  for their integrated run).

## Tests

- Full suite green on the adopted tree (123 tests at item-1 commit, 126 at
  item-3/4 commit including new thesis-aware layer-2 and direction-model
  tests; CTO's test_mapped_events adds more).
