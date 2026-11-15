# UTradeDashboard

Repo for the **AlgoSignal Lab** trading research platform and the **NewSetup**
Supply Chain Inefficiency (SCI) trading environment.

- Live dashboard (GitHub Pages): https://ugurzafercandan.github.io/UTradeDashboard/
- This README is the master index: every key document and method in the repo
  is listed here with a link and a one-line description.

## What lives in this repo

| Path | What it is |
|------|------------|
| `index.html` | AlgoSignal Lab dashboard (signals, live trading, scorecards, research cards). Served via GitHub Pages. |
| `pt_config_expserver.json` | Live config for the 22 production MT5 EA signals (symbol, model, magic number, thresholds, stops). |
| `update_frontend.py` | Export job: pulls live paper trades from `paper_trades_v2.db` into `results/live_paper_trades.json` for the dashboard. Usage and cron pattern documented in its docstring. |
| `results/` | Machine-generated result artifacts backing the dashboard (see table below). |
| `trading_system_analysis.md` | Comprehensive written analysis of the AlgoSignal Lab system (models, validation, portfolio, results). |
| `NewSetup/` | SCI trading playbook implementation + testing environment (own README). |

## Key documents

| Document | Content |
|----------|---------|
| [trading_system_analysis.md](trading_system_analysis.md) | Full analysis of the AlgoSignal Lab platform: 5 ML models (XGBoost, LightGBM, CatBoost, RF, logistic), feature-set evolution (45 -> Enhanced65 -> research100), labeling methods, 8-fold walk-forward validation (2021-2024), quality gates, production signal portfolio P6-P81 in confidence tiers A/B/C, experiment waves A-G, live forward-testing results and P&L, position-stacking bug fix (USO-408), instrument coverage, infrastructure. |
| [NewSetup/README.md](NewSetup/README.md) | SCI testing & trading environment: directory layout, 3-layer signal pipeline, usage commands, testing & acceptance gates, signal quality + degradation monitoring, phase status (0-5), safety rules. |
| [NewSetup/docs/sci_playbook_v1.md](NewSetup/docs/sci_playbook_v1.md) | **Supply Chain Inefficiency Trading Playbook v1.0** — the source spec implemented by NewSetup: thesis, capital plan ($5K -> $15K -> $50K), phase 0-5 plan, instrument map for all 40 inefficiencies, 3-layer signal system, risk rules. Appendices: A (40 trade cards), B (forex strategies), C (event responses), D (risk management). Encoded into `NewSetup/config/*.yaml` by `scripts/generate_playbook_config.py`. |
| [NewSetup/backtest/results/validation_report.md](NewSetup/backtest/results/validation_report.md) | Honest synthetic-data validation of the NewSetup backtest harness (what passed, what the numbers do and do not prove). |
| [NewSetup/backtest/results/realdata_event_backtests.md](NewSetup/backtest/results/realdata_event_backtests.md) | Real-data event-window backtests (playbook 5.2): COVID-19 2020, Suez 2021, Russia sanctions 2022, Red Sea 2023-24, China power 2021, with per-event acceptance-gate results. Per-run JSON data sits alongside it. |

## Result artifacts (`results/`)

| File | Content |
|------|---------|
| `live_paper_trades.json` | Live paper trading records exported by `update_frontend.py` for the dashboard. |
| `algo_forward_testing.json` | Forward-testing performance per algo (drives the Algo Forward-Testing dashboard tab). |
| `leaderboard.json` | Raw experiment leaderboard from the research sweeps (run_id, model, symbol, horizon, accuracy, Sharpe, drawdown, P&L). |
| `mt5_closed_orders.json`, `mt5_open_orders.json` | MT5 account state snapshots used by the dashboard. |
| `mt5_tester_2025_results.json` | MT5 strategy tester results for 2025. |
| `uso175_qc_validation_result.json` | QC validation verdicts per signal/config (PASS/FAIL with QC Sharpe). |
| `uso385_gdelt_news_results.json` | USO-385 GDELT + economic-calendar news experiment results (72-config sweep). |
| `wave_e_rf_results.tsv`, `wave_g_lgb_results.tsv` | Raw per-run results for the Random Forest (Wave E) and LightGBM (Wave G) sweeps. |

## Methods

### AlgoSignal Lab (ML signal research)

Documented in depth in [trading_system_analysis.md](trading_system_analysis.md):

- **Models**: XGBoost, LightGBM, CatBoost, Random Forest, Logistic Regression.
- **Features**: technical indicators, momentum ranks, Garman-Klass volatility;
  feature sets evolved 45 -> Enhanced65 (production standard) -> research100 (86 features).
- **Labeling**: simple directional, triple-barrier, volatility-adjusted thresholds.
- **Timeframe**: H1 bars; lookforward windows 30/60/120/240 bars.
- **Validation**: 8-fold walk-forward (2021-2024) with QC gates (QC Sharpe PASS/FAIL,
  see `results/uso175_qc_validation_result.json`); 28,000+ experiments across waves A-G.
- **Production**: 22 signals of 81 candidates run live paper trading via MT5
  (config in `pt_config_expserver.json`); results flow through
  `update_frontend.py` into the dashboard.

### NewSetup (SCI trading environment)

Documented in depth in [NewSetup/README.md](NewSetup/README.md), spec in
[NewSetup/docs/sci_playbook_v1.md](NewSetup/docs/sci_playbook_v1.md):

- **Signal pipeline**: layer-1 scanner (40 inefficiencies, EVENT/PRICE/SENTIMENT/DATA
  triggers over GDELT, RSS, MT5, FinBERT) -> layer-2 confirmation (RSI/SMA/sentiment
  score) -> layer-3 portfolio sizing (0.5% risk, ATR stops, exposure caps) -> signal
  bus -> execution (paper broker, risk enforcer, MT5 bridge).
- **Backtesting & gates**: event-driven runner, analyzer with acceptance gate
  (>=30 trades, DD <=12%, Sharpe >=1.0, WR >=48%, PF >=1.3), walk-forward optimizer
  (WFER >= 0.5), A/B scaffold with t-test gating.
- **Monitoring**: signal-quality funnel tracking, automated degradation ladder
  (ok -> reduce_size -> paused -> retired), daily reports, alerting.
- **Safety**: paper mode by default; live MT5 execution gated on phase 3/4
  acceptance criteria; Appendix D risk limits enforced in code.

## Running

    # NewSetup: one full pipeline cycle, offline (synthetic prices + fixture events)
    C:/Python314/python.exe NewSetup/main.py --once --offline

    # NewSetup: daily report / synthetic validation harness
    C:/Python314/python.exe NewSetup/main.py --report
    C:/Python314/python.exe NewSetup/main.py --validate

    # NewSetup: test suite (pytest; pyyaml + pytest required)
    C:/Python314/python.exe -m pytest NewSetup -q

    # Dashboard refresh: export live paper trades to results/live_paper_trades.json
    python update_frontend.py

`NewSetup/requirements.txt` lists core dependencies; the live-data/ML stack
(MetaTrader5, transformers, torch, pandas, ...) is commented in and installed
only when needed.

## Notes

- NewSetup result reports are deliberately honest: synthetic-data results are
  labelled as plumbing checks, and acceptance gates are expected to FAIL
  strategies without a real edge. See the validation report.
- Machine-generated caches, logs and databases (`NewSetup/db/newsetup.sqlite3`,
  `NewSetup/logs/`, `NewSetup/data/caches/`, `.pytest_cache/`) are runtime state,
  not documentation.
