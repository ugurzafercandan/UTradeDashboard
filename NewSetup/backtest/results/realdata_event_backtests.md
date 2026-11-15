# Real-data event-window backtests (playbook 5.2)

Data: MT5 terminal D1 bars (data/caches/). Signals: layer-1
PRICE trigger replay (GDELT DOC 2.0 only covers recent months
so EVENT triggers cannot fire on 2020-2024 history).

## covid_2020 — COVID-19 global supply shock

Window: 2020-02-15 .. 2020-06-30 | symbols: 12 (skipped 31) | raw signals: 70

- Trades: 6
- Win rate: 16.7%
- Profit factor: 0.49
- Sharpe: -0.24 | Sortino: -0.31
- Max drawdown: 0.16%
- Total return: -0.11%
- Final equity: 9989.44 (start 10000)
- Acceptance: FAIL — min_trades not met: total_trades 6 < 30, min_win_rate_pct not met: win_rate_pct 16.6667 < 48.0, min_profit_factor not met: profit_factor 0.4865 < 1.3, min_sharpe not met: sharpe -0.2413 < 1.0

## suez_2021 — Suez Canal Ever Given blockage

Window: 2021-03-10 .. 2021-04-20 | symbols: 12 (skipped 31) | raw signals: 11

- Trades: 0
- Win rate: 0.0%
- Profit factor: 0.00
- Sharpe: 0.00 | Sortino: 0.00
- Max drawdown: 0.00%
- Total return: 0.00%
- Final equity: 10000.00 (start 10000)
- Acceptance: FAIL — min_trades not met: total_trades 0 < 30, min_win_rate_pct not met: win_rate_pct 0.0 < 48.0, min_profit_factor not met: profit_factor 0.0 < 1.3, min_sharpe not met: sharpe 0.0 < 1.0

## china_power_2021 — China energy crisis / power rationing

Window: 2021-09-01 .. 2021-11-15 | symbols: 13 (skipped 30) | raw signals: 25

- Trades: 2
- Win rate: 0.0%
- Profit factor: 0.00
- Sharpe: -0.45 | Sortino: -0.46
- Max drawdown: 0.10%
- Total return: -0.10%
- Final equity: 9989.99 (start 10000)
- Acceptance: FAIL — min_trades not met: total_trades 2 < 30, min_win_rate_pct not met: win_rate_pct 0.0 < 48.0, min_profit_factor not met: profit_factor 0.0 < 1.3, min_sharpe not met: sharpe -0.4525 < 1.0

## russia_sanctions_2022 — Russia sanctions / commodity squeeze

Window: 2022-02-15 .. 2022-04-30 | symbols: 13 (skipped 30) | raw signals: 27

- Trades: 2
- Win rate: 100.0%
- Profit factor: 999.00
- Sharpe: 0.47 | Sortino: 0.82
- Max drawdown: 0.07%
- Total return: 0.20%
- Final equity: 10019.95 (start 10000)
- Acceptance: FAIL — min_trades not met: total_trades 2 < 30, min_sharpe not met: sharpe 0.4653 < 1.0

## red_sea_2023_24 — Red Sea shipping attacks

Window: 2023-11-01 .. 2024-03-31 | symbols: 37 (skipped 6) | raw signals: 319

- Trades: 19
- Win rate: 10.5%
- Profit factor: 0.27
- Sharpe: -0.25 | Sortino: -0.32
- Max drawdown: 0.54%
- Total return: -0.53%
- Final equity: 9946.75 (start 10000)
- Acceptance: FAIL — min_trades not met: total_trades 19 < 30, min_win_rate_pct not met: win_rate_pct 10.5263 < 48.0, min_profit_factor not met: profit_factor 0.2691 < 1.3, min_sharpe not met: sharpe -0.2517 < 1.0
