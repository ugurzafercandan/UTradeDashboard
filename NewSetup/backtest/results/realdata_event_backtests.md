# Real-data event-window backtests (playbook 5.2)

Data: MT5 terminal D1 bars (data/caches/). Signals: layer-1
PRICE trigger replay (GDELT DOC 2.0 only covers recent months
so EVENT triggers cannot fire on 2020-2024 history).

## covid_2020 — COVID-19 global supply shock

Window: 2020-02-15 .. 2020-06-30 | symbols: 15 (skipped 33) | raw signals: 98

- Trades: 11
- Win rate: 9.1%
- Profit factor: 0.24
- Sharpe: -0.43 | Sortino: -0.53
- Max drawdown: 0.32%
- Total return: -0.32%
- Final equity: 9967.84 (start 10000)
- Acceptance: FAIL — min_trades not met: total_trades 11 < 30, min_win_rate_pct not met: win_rate_pct 9.0909 < 48.0, min_profit_factor not met: profit_factor 0.2361 < 1.3, min_sharpe not met: sharpe -0.4292 < 1.0

## suez_2021 — Suez Canal Ever Given blockage

Window: 2021-03-10 .. 2021-04-20 | symbols: 27 (skipped 21) | raw signals: 64

- Trades: 2
- Win rate: 0.0%
- Profit factor: 0.00
- Sharpe: -0.19 | Sortino: -0.21
- Max drawdown: 0.07%
- Total return: -0.05%
- Final equity: 9994.67 (start 10000)
- Acceptance: FAIL — min_trades not met: total_trades 2 < 30, min_win_rate_pct not met: win_rate_pct 0.0 < 48.0, min_profit_factor not met: profit_factor 0.0 < 1.3, min_sharpe not met: sharpe -0.1912 < 1.0

## china_power_2021 — China energy crisis / power rationing

Window: 2021-09-01 .. 2021-11-15 | symbols: 36 (skipped 12) | raw signals: 157

- Trades: 8
- Win rate: 12.5%
- Profit factor: 0.11
- Sharpe: -0.31 | Sortino: -0.36
- Max drawdown: 0.32%
- Total return: -0.31%
- Final equity: 9968.84 (start 10000)
- Acceptance: FAIL — min_trades not met: total_trades 8 < 30, min_win_rate_pct not met: win_rate_pct 12.5 < 48.0, min_profit_factor not met: profit_factor 0.108 < 1.3, min_sharpe not met: sharpe -0.308 < 1.0

## russia_sanctions_2022 — Russia sanctions / commodity squeeze

Window: 2022-02-15 .. 2022-04-30 | symbols: 37 (skipped 11) | raw signals: 226

- Trades: 7
- Win rate: 42.9%
- Profit factor: 1.72
- Sharpe: 0.12 | Sortino: 0.18
- Max drawdown: 0.19%
- Total return: 0.12%
- Final equity: 10012.40 (start 10000)
- Acceptance: FAIL — min_trades not met: total_trades 7 < 30, min_win_rate_pct not met: win_rate_pct 42.8571 < 48.0, min_sharpe not met: sharpe 0.1199 < 1.0

## red_sea_2023_24 — Red Sea shipping attacks

Window: 2023-11-01 .. 2024-03-31 | symbols: 43 (skipped 5) | raw signals: 383

- Trades: 22
- Win rate: 31.8%
- Profit factor: 0.92
- Sharpe: -0.02 | Sortino: -0.03
- Max drawdown: 0.31%
- Total return: -0.05%
- Final equity: 9995.18 (start 10000)
- Acceptance: FAIL — min_trades not met: total_trades 22 < 30, min_win_rate_pct not met: win_rate_pct 31.8182 < 48.0, min_profit_factor not met: profit_factor 0.922 < 1.3, min_sharpe not met: sharpe -0.022 < 1.0
