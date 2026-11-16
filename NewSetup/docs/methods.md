# NewSetup — Methods Reference

Per-module method documentation for the NewSetup SCI (Supply Chain
Inefficiency) trading environment, describing the committed code.
The source spec is [sci_playbook_v1.md](sci_playbook_v1.md); the module
layout and usage summary live in the [NewSetup README](../README.md).

## Shared core (`newsetup/`)

- `models.py` — plain dataclasses shared by every layer:
  `Trigger`, `Inefficiency`, `Event`, `PriceBar`, `RawSignal` (layer-1
  output), `ConfirmedSignal` (layer-2 output), `SizedSignal` (layer-3
  output; field names mirror the `active_signals.json` Python -> MQL5
  format of playbook 4.4), `AccountState`, `Trade`.
- `config.py` — YAML loaders returning domain objects:
  `load_settings`, `load_instruments`, `load_trade_cards` (Appendix A,
  the 40 trade cards keyed by inefficiency id), `load_fx_strategies`
  (Appendix B, FX-1..FX-6), `load_event_responses` (Appendix C,
  C.1..C.7), `load_gdelt_keywords`, `load_broker_map`
  (playbook-symbol -> broker-symbol map),
  `load_inefficiencies` (all 40 defs with triggers) and `sector_for`
  (correlation-sector grouping behind the Appendix D exposure caps).
- `indicators.py` — pure functions: `sma`, `rsi`, `atr`, `pct_change`.

## Data layer (`data/`) — playbook section 2.3

- `gdelt_monitor.py` — `GDELTMonitor.get_events()` queries the GDELT
  DOC 2.0 API (`ArtList`, 50 records, date-desc) with per-inefficiency
  keyword theming from `config/gdelt_keywords.yaml`. Live results are
  cached for 300 s (the API allows about one request per 5 s, and the
  scanner evaluates up to 40 inefficiencies per cycle); a failed query
  is retried once after 6 s and otherwise degrades to bundled fixture
  events (`data/fixtures/sample_events.json`), so `--offline` and the
  test suite never need the network. Events carry a 0..1 relevance
  score on the shared `Event` model.
- `rss_monitor.py` — `RssMonitor.get_events()` pulls the playbook's
  priority RSS feeds (Reuters, Bloomberg, FT, OilPrice, Mining.com,
  EU agriculture) with stdlib only (`urllib` + `xml.etree`), filters
  headlines against the same keyword themes and maps items to
  `Event`s. Feed failures degrade per-feed; if nothing is fetched the
  offline event fixtures are returned.
- `sentiment.py` — `FinBERTSentiment.score()` returns a sentiment in
  [-1, 1] (negative = supply-threat / risk-off tone) using the
  transformers `ProsusAI/finbert` pipeline when available, otherwise a
  lexicon-based fallback scorer (`NEWSETUP_DISABLE_TRANSFORMERS=1`
  forces the fallback). Theme scores are cached per headline.
- `price_provider.py` — `MT5PriceProvider.get_series()` pulls D1 bars
  via the optional MetaTrader5 python package when the terminal is
  reachable; `SyntheticPriceProvider` generates deterministic
  seeded random walks from realistic base prices; and
  `default_price_provider()` selects MT5 when available, synthetic
  otherwise, so the paper pipeline runs identically offline.

## Signal pipeline (`signals/`) — playbook section 4

1. `layer1_scanner.py` — evaluates every inefficiency's EVENT / PRICE /
   SENTIMENT / DATA triggers against the pluggable providers above and
   emits `RawSignal`s (with trigger description and confidence).
2. `layer2_confirmation.py` — RSI + SMA trend + sentiment checks
   produce a 0..1 score; signals below `layer2.min_score` are dropped,
   survivors become `ConfirmedSignal`s.
3. `layer3_portfolio.py` — fixed-fractional sizing at 0.5% account risk
   per trade, ATR(14)x2 stops and 2R targets; caps: max 7 open
   positions, one position per inefficiency, per-sector exposure and
   portfolio heat. Output is `SizedSignal`s.
4. `signal_bus.py` — `SignalBus.emit()` persists the current signal set
   as `active_signals.json` in exactly the format the MQL5 EA reads
   (playbook 4.4): `{"last_updated": <iso-utc>, "signals":
   [<SizedSignal dicts>]}`; `load()` reads it back for round-trip
   tests.
5. `event_responses.py` / `fx_strategies.py` — the Appendix C event
   response playbooks and Appendix B FX strategy definitions, joined
   by inefficiency id.

## Execution (`execution/`) — playbook section 7

- `order_manager.py` — `OrderManager.place()` routes each sized signal
  to the active broker through the `RiskEnforcer` gate; rejections are
  recorded as `(SizedSignal, reason)` pairs for the monitoring layer
  (playbook 7.4).
- `risk_enforcer.py` — `RiskEnforcer.check()` enforces Appendix D in
  order: margin cap, max open positions, per-sector exposure cap and
  portfolio heat, plus drawdown circuit breakers at 5% (warn) / 8%
  (reduce) / 12% (halt) of equity.
- `paper_broker.py` — `PaperBroker` simulates Pepperstone Razor fills
  with a spread cost, resolves SL/TP on each bar, and tracks account
  equity / open trades for the enforcer.
- `mt5_bridge.py` — `MT5Bridge` wraps the MetaTrader5 package for
  live/demo order placement; the module imports cleanly on hosts
  without the terminal and raises `MT5NotAvailable` on use.

## Backtesting & validation (`backtest/`) — playbook section 5

- `runner.py` — `BacktestRunner.run()` replays historical bars
  chronologically through layer-2 confirmation and layer-3 sizing
  against a broker (`InMemoryPrices` replay cursor plus an internal
  `_SimBroker` with the same submit/on_bar/account_state interface as
  `PaperBroker`); flat or nested parameter overrides are deep-merged
  into settings per run.
- `analyzer.py` — `BacktestAnalyzer` computes Sharpe, Sortino, max
  drawdown, win rate and profit factor, and applies the hard
  acceptance gate (playbook 5.3): >= 30 trades, max DD <= 12%,
  Sharpe >= 1.0, win rate >= 48%, PF >= 1.3. Per-window Sharpe for
  the 5.3 window gate uses the daily-aggregated convention:
  per-point Sharpe on intraday H1 windows is deflated by ~sqrt(24),
  so window Sharpe is computed on daily-aggregated equity
  (`scripts/window_sharpe_daily.py`, commit 9f866db).
- `walk_forward.py` — `WalkForwardOptimizer` slides train/test windows
  across the merged multi-symbol timeline, tunes layer-2/3 parameters
  on the in-sample segment and scores the out-of-sample segment; the
  walk-forward efficiency ratio (OOS/IS Sharpe) must be >= 0.5
  (playbook 5.5).
- `ab_testing.py` — A/B scaffold (playbook 9.5): paired per-fold
  comparison of a candidate variant against the baseline with a
  t-test gate. Each fold's bars include `ab_testing.warmup_days`
  (default 400) of warmup history BEFORE the fold start; without it
  every fold signal fails layer-2 "insufficient history"
  (`min_history_bars` cannot warm up inside a bare slice) and the
  paired comparison degenerates to mean_diff=0 / p=1 on both arms.
  Fold signals stay strictly inside the fold window, so fold metrics
  stay fold-pure. Adopting a candidate additionally requires passing
  the 5.3 acceptance gate and 5.5 walk-forward on out-of-sample REAL
  data.
- `validation.py` — synthetic-data harness validation
  (`main.py --validate`): deterministic trend + cycle + noise bars,
  BUY signals at deterministic oversold dips, a full pass of every
  inefficiency's primary instrument through runner + analyzer, plus
  9.2 / 9.4 / 9.5 demos; renders the honest
  [results/validation_report.md](../backtest/results/validation_report.md).

## Monitoring (`monitoring/`) — playbook sections 8-9

- `quality_tracker.py` (9.2) — `SignalQualityTracker` persists the
  per-inefficiency funnel (fired -> confirmed -> traded -> won, gross
  PnL) into the SQLite store and aggregates monthly `signal_quality`
  rows.
- `degradation.py` (9.4) — `DegradationDetector` runs rolling 30-day
  win-rate and Sharpe checks per inefficiency and escalates through
  the automated response ladder ok -> reduce_size (0.5x) -> paused ->
  retired; state persists in `degradation_state` and `main.py` applies
  the responses to sizing before every cycle.
- `alerter.py` (8.1) — log-based alerts at info / warning / critical
  levels, with an optional Telegram channel for critical alerts
  (`TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` env vars).
- `daily_report.py` (8.2) — `daily_report()` renders a markdown daily
  P&L / status report from the broker's account state
  (`main.py --report`).

## Persistence (`db/`)

- `schema.sql` — SQLite tables: `events`, `inefficiencies`, `signals`
  (layer scores, lot, SL/TP, status), `trades`, `signal_quality` and
  `degradation_state`.
- `store.py` — `NewSetupDB` applies the schema on open and provides the
  typed accessors used by the signal pipeline, quality tracker and
  degradation detector.

## Orchestrator (`main.py`) — playbook 4.5

`build_pipeline()` wires providers -> scanner -> confirmation ->
portfolio -> signal bus -> risk enforcer -> paper broker.
`run_signal_pipeline()` runs one cycle: scan -> confirm -> size -> emit
-> execute (paper). `_apply_degradation_responses()` filters
paused/retired inefficiencies and scales lots for `reduce_size` before
each cycle. CLI flags:

    --once      one pipeline cycle
    --loop      scheduled loop
    --report    print the daily report
    --validate  synthetic harness validation -> results/validation_report.md
    --offline   force offline providers (fixtures + synthetic prices)

## Running / testing

    # install core deps (live-data / ML stack is optional; see file comments)
    C:/Python314/python.exe -m pip install -r NewSetup/requirements.txt

    # test suite
    C:/Python314/python.exe -m pytest NewSetup -q

    # one offline cycle / daily report / harness validation
    C:/Python314/python.exe NewSetup/main.py --once --offline
    C:/Python314/python.exe NewSetup/main.py --report
    C:/Python314/python.exe NewSetup/main.py --validate

    # regenerate config/*.yaml from the playbook source (do not hand-edit)
    C:/Python314/python.exe NewSetup/scripts/generate_playbook_config.py

`scripts/generate_playbook_config.py` parses Appendices A-C directly
out of `docs/sci_playbook_v1.md`, builds the per-inefficiency GDELT
keyword themes, validates the result against the config loaders, and
rewrites `config/trade_cards.yaml`, `config/fx_strategies.yaml`,
`config/event_responses.yaml` and `config/gdelt_keywords.yaml` with a
"generated, do not hand-edit" header.

## Runtime artifacts (never committed)

`db/*.sqlite3`, `logs/`, `data/caches/`, `active_signals.json` and
`backtest/results/*.json` are generated state — see the root
`.gitignore` and `NewSetup/.gitignore`. Committed reports
(`backtest/results/validation_report.md`) are the exception: they are
checked-in documentation.