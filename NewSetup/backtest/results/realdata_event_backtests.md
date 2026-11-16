# Real-data event-window backtests (playbook 5.2)

Data: MT5 terminal D1 bars (data/caches/). Signals: layer-1
PRICE trigger replay (GDELT DOC 2.0 only covers recent months
so EVENT triggers cannot fire on 2020-2024 history).

## covid_2020 — COVID-19 global supply shock

Window: 2020-02-15 .. 2020-06-30 | symbols: 21 (skipped 27) | raw signals: 374

- Trades: 106
- Win rate: 43.4%
- Profit factor: 1.50
- Sharpe: 0.09 | Sortino: 0.14
- Max drawdown: 0.83%
- Total return: 1.52%
- Final equity: 10151.68 (start 10000)
- Acceptance: FAIL — min_win_rate_pct not met: win_rate_pct 43.3962 < 48.0, min_sharpe not met: sharpe 0.094 < 1.0

## suez_2021 — Suez Canal Ever Given blockage

Window: 2021-03-10 .. 2021-04-20 | symbols: 27 (skipped 21) | raw signals: 103

- Trades: 36
- Win rate: 44.4%
- Profit factor: 1.50
- Sharpe: 0.05 | Sortino: 0.07
- Max drawdown: 0.51%
- Total return: 0.51%
- Final equity: 10051.08 (start 10000)
- Acceptance: FAIL — min_win_rate_pct not met: win_rate_pct 44.4444 < 48.0, min_sharpe not met: sharpe 0.0484 < 1.0

## china_power_2021 — China energy crisis / power rationing

Window: 2021-09-01 .. 2021-11-15 | symbols: 36 (skipped 12) | raw signals: 204

- Trades: 78
- Win rate: 44.9%
- Profit factor: 1.58
- Sharpe: 0.08 | Sortino: 0.12
- Max drawdown: 0.36%
- Total return: 1.22%
- Final equity: 10121.93 (start 10000)
- Acceptance: FAIL — min_win_rate_pct not met: win_rate_pct 44.8718 < 48.0, min_sharpe not met: sharpe 0.0789 < 1.0

## russia_sanctions_2022 — Russia sanctions / commodity squeeze

Window: 2022-02-15 .. 2022-04-30 | symbols: 37 (skipped 11) | raw signals: 376

- Trades: 107
- Win rate: 37.4%
- Profit factor: 1.11
- Sharpe: 0.02 | Sortino: 0.03
- Max drawdown: 0.75%
- Total return: 0.37%
- Final equity: 10036.66 (start 10000)
- Acceptance: FAIL — min_win_rate_pct not met: win_rate_pct 37.3832 < 48.0, min_profit_factor not met: profit_factor 1.1082 < 1.3, min_sharpe not met: sharpe 0.0199 < 1.0

## red_sea_2023_24 — Red Sea shipping attacks

Window: 2023-11-01 .. 2024-03-31 | symbols: 43 (skipped 5) | raw signals: 574

- Trades: 105
- Win rate: 42.9%
- Profit factor: 1.41
- Sharpe: 0.07 | Sortino: 0.10
- Max drawdown: 0.45%
- Total return: 1.27%
- Final equity: 10126.81 (start 10000)
- Acceptance: FAIL — min_win_rate_pct not met: win_rate_pct 42.8571 < 48.0, min_sharpe not met: sharpe 0.0702 < 1.0
