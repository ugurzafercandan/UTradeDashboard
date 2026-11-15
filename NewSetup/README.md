# NewSetup — Supply Chain Inefficiency Trading & Testing Environment

Implementation of the **Supply Chain Inefficiency Trading Playbook v1.0**
(Pepperstone MT5): 40 structural supply-chain inefficiencies -> tradeable
signals across forex, commodity CFD, ETF CFD and equity CFD instruments,
with a full testing stack (unit tests, backtests, walk-forward) and a
paper-trading environment before any live deployment.

## Layout (playbook section 2.6)

    NewSetup/
    ├── config/            settings.yaml, instruments.yaml, inefficiencies.yaml (40 defs)
    ├── newsetup/          shared core: models, config loader, indicators
    ├── data/              GDELT monitor, FinBERT sentiment, RSS, price providers
    ├── signals/           layer1_scanner, layer2_confirmation, layer3_portfolio, signal_bus
    ├── execution/         paper broker, order manager, MT5 bridge, risk enforcer
    ├── backtest/          runner, analyzer (Sharpe/DD/win-rate), walk-forward optimizer
    ├── monitoring/        alerter (Telegram-capable), daily report
    ├── db/                SQLite schema (signals, trades, signal_quality)
    ├── tests/             pytest suite (signals, execution, risk, backtest, data)
    ├── main.py            orchestrator: scan -> confirm -> size -> emit -> execute
    └── active_signals.json  Python -> MQL5 signal file (playbook 4.4 format)

## Signal pipeline (playbook section 4)

1. **Layer 1 — Scanner** (`signals/layer1_scanner.py`): evaluates all 40
   inefficiencies' EVENT / PRICE / SENTIMENT / DATA triggers against
   pluggable providers (GDELT, MT5/synthetic prices, FinBERT).
2. **Layer 2 — Confirmation** (`signals/layer2_confirmation.py`): RSI +
   SMA trend + sentiment checks produce a 0..1 score; below
   `layer2.min_score` the signal is dropped.
3. **Layer 3 — Portfolio** (`signals/layer3_portfolio.py`): fixed-fractional
   sizing (0.5% risk/trade), ATR(14)x2 stops, 2R targets, caps: max 7 open
   positions, one per inefficiency, sector exposure and portfolio heat.
4. **Signal bus** (`signals/signal_bus.py`): writes `active_signals.json`
   in the exact format the MQL5 EA reads (playbook 4.4).
5. **Execution** (`execution/`): paper broker with spread + SL/TP
   simulation, risk enforcer implementing Appendix D hard limits and
   drawdown circuit breakers (5% / 8% / 12%), MT5 bridge for live use.

## Usage

    # one pipeline cycle, fully offline (synthetic prices + fixture events)
    C:/Python314/python.exe NewSetup/main.py --once --offline

    # daily report
    C:/Python314/python.exe NewSetup/main.py --report

    # run the test suite
    C:/Python314/python.exe -m pytest NewSetup -q

## Testing & acceptance (playbook sections 5, 9)

- `backtest/runner.py` — event-driven replay over bar data with any
  broker implementing submit/on_bar/account_state.
- `backtest/analyzer.py` — Sharpe, Sortino, max drawdown, win rate,
  profit factor; acceptance gate: >=30 trades, DD <=12%, Sharpe >=1.0,
  win rate >=48%, PF >=1.3.
- `backtest/walk_forward.py` — sliding-window optimizer with
  walk-forward efficiency ratio (OOS/IS Sharpe >= 0.5).

## Phase status (playbook phases)

- Phase 0 infrastructure: DONE (this scaffold, tests green)
- Phase 1 instrument mapping: DONE (config/*.yaml generated from playbook 3.1)
- Phase 2 signal engine: CORE DONE (3 layers + bus; GDELT/FinBERT/MT5 live feeds pending)
- Phase 3 backtesting: HARNESS DONE (real historical data pending)
- Phase 4 paper trading: READY (paper broker + risk enforcer; 4-week rollout pending)
- Phase 5 live deployment: NOT STARTED (gated on phases 3-4 acceptance)

## Safety

Paper mode is the default. Live MT5 execution requires explicitly
switching `general.mode` to `live` and passing Phase 3/4 acceptance
criteria. Risk limits (Appendix D) are enforced in code, not docs.
