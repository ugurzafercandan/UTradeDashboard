# NewSetup Validation Report (synthetic data)

Generated: 2026-11-15 18:33 UTC — by the backtest/validation harness (backtest/validation.py).

## 1. What was run

- 40 inefficiencies; 36 exercisable on synthetic bars via their primary Pepperstone instrument
- Deterministic synthetic series: 1300 H1 bars per instrument (trend + cycle + seeded LCG noise), BUY signals at RSI(5)<=25 dips
- Full replay per inefficiency: BacktestRunner (layer 2 confirm + layer 3 sizing + simulated fills with 0.02% spread), acceptance gate (>=30 trades, maxDD <=12%, Sharpe >=1.0, WR >=48%, PF >=1.3), plus walk-forward (train 250 / test 62 bars, grid rsi_oversold {25, 30}, WFER >= 0.5)

## 2. Aggregate results (SYNTHETIC — harness plumbing check only)

- Inefficiencies tested: 36/40 (4 had no instrument map and were skipped)
- Trades per inefficiency: min 81, median 82, max 82
- Acceptance gate PASSED on synthetic data: 0/36
- Walk-forward WFER >= 0.5: 26/36

Reading these numbers honestly:

- The acceptance gate is NOT a rubber stamp: 0/36 synthetic runs passed. The 'trend + oversold dip' synthetic strategy wins only ~30-42% of its trades, so the gate correctly refuses to certify an edge that is not there. That is the expected behaviour of a working gate.
- Even the 26 WFER 'passes' prove nothing: many are artifacts of near-zero in-sample Sharpe (e.g. WFER 48.78 when IS Sharpe ~ 0.04), exactly the weakness called out in blind spot 6 below.
- Sample sizes are real (82 trades per run), but the DATA is synthetic: none of these numbers say anything about live edge.

## 3. Per-inefficiency results (synthetic)

| # | inefficiency | symbol | signals | trades | WR% | PF | Sharpe | maxDD% | accept | WFER |
|---|--------------|--------|---------|--------|-----|----|--------|--------|--------|------|
| 1 | Helium | LIN.US | 82 | 82 | 39.0 | 1.26 | 0.73 | 0.3 | FAIL | -0.45 (fail) |
| 2 | Antimony | USDCNH | 82 | 82 | 31.7 | 0.92 | -0.27 | 0.7 | FAIL | 2.17 |
| 3 | Gallium/Germanium | USDCNH | 82 | 82 | 29.3 | 0.81 | -0.64 | 0.9 | FAIL | 2.35 |
| 4 | Graphite | USDCNH | 82 | 82 | 36.6 | 1.13 | 0.38 | 0.4 | FAIL | -1.73 (fail) |
| 5 | Manganese | USDZAR | 82 | 82 | 34.1 | 1.01 | 0.04 | 0.5 | FAIL | 3.51 |
| 6 | Fluorspar | USDCNH | 82 | 82 | 32.9 | 0.96 | -0.14 | 0.6 | FAIL | 2.39 |
| 7 | Phosphate Rock | MOS.US | 82 | 82 | 25.6 | 0.69 | -1.17 | 1.3 | FAIL | 2.26 |
| 8 | Rare Earth Refining | USDCNH | 82 | 82 | 34.1 | 1.02 | 0.08 | 0.5 | FAIL | 5.54 |
| 9 | Cobalt | COPPER | 82 | 82 | 30.5 | 0.87 | -0.45 | 0.7 | FAIL | 2.39 |
| 10 | Uranium Enrichment | USDCAD | 82 | 81 | 42.0 | 1.42 | 1.10 | 0.2 | FAIL | 0.44 (fail) |
| 11 | Titanium Sponge | USDCNH | 82 | 82 | 29.3 | 0.81 | -0.65 | 1.0 | FAIL | 2.01 |
| 12 | Magnesium | USDCNH | 82 | 82 | 34.1 | 1.01 | 0.04 | 0.4 | FAIL | 48.78 |
| 13 | Potash | USDCAD | 82 | 82 | 39.0 | 1.25 | 0.71 | 0.4 | FAIL | -4.32 (fail) |
| 14 | Seed Genetics | DE.US | 82 | 82 | 31.7 | 0.92 | -0.26 | 0.6 | FAIL | 3.02 |
| 15 | Pollination | DAR.US | 82 | 82 | 36.6 | 1.14 | 0.41 | 0.3 | FAIL | 16.86 |
| 16 | Refrigerant Gases | USDCNH | 82 | 82 | 34.1 | 1.03 | 0.08 | 0.4 | FAIL | 3.79 |
| 17 | Container Imbalance | ZIM.US | 82 | 82 | 29.3 | 0.81 | -0.65 | 0.8 | FAIL | 2.32 |
| 18 | Panama Canal | ZIM.US | 82 | 82 | 35.4 | 1.07 | 0.22 | 0.6 | FAIL | 0.03 (fail) |
| 19 | Red Sea / Suez | XTIUSD | 82 | 82 | 28.0 | 0.76 | -0.84 | 0.8 | FAIL | 2.06 |
| 20 | Vanilla | - | - | - | - | - | - | - | error: no Pepperstone instrument mapped | - |
| 21 | Palm Oil | - | - | - | - | - | - | - | error: no Pepperstone instrument mapped | - |
| 22 | Fishmeal | MOWI.US | 82 | 82 | 29.3 | 0.82 | -0.62 | 0.9 | FAIL | 1.74 |
| 23 | Cocoa | COCOA | 82 | 82 | 41.5 | 1.40 | 1.02 | 0.4 | FAIL | -2.65 (fail) |
| 24 | Natural Rubber | - | - | - | - | - | - | - | error: no Pepperstone instrument mapped | - |
| 25 | Bauxite/Alumina | ALUMINIUM | 82 | 82 | 35.4 | 1.07 | 0.22 | 0.3 | FAIL | -17.89 (fail) |
| 26 | Wheat Chokepoints | WHEAT | 82 | 81 | 33.3 | 0.98 | -0.06 | 0.5 | FAIL | 2.48 |
| 27 | Undersea Cables | TE.US | 82 | 82 | 37.8 | 1.18 | 0.54 | 0.5 | FAIL | 35.34 |
| 28 | ASML Monopoly | EURUSD | 82 | 82 | 34.1 | 1.03 | 0.09 | 0.5 | FAIL | 4.06 |
| 29 | TSMC Concentration | SOXX.US | 82 | 82 | 37.8 | 1.20 | 0.58 | 0.4 | FAIL | -4.10 (fail) |
| 30 | Neon Gas | SOXX.US | 82 | 82 | 36.6 | 1.14 | 0.40 | 0.5 | FAIL | 3.18 |
| 31 | Ultra-Pure Water | USDJPY | 82 | 82 | 29.3 | 0.82 | -0.63 | 0.9 | FAIL | 2.38 |
| 32 | SWIFT System | EURUSD | 82 | 82 | 26.8 | 0.72 | -1.01 | 1.1 | FAIL | 2.78 |
| 33 | GPS/GNSS | LMT.US | 82 | 81 | 34.6 | 1.03 | 0.11 | 0.4 | FAIL | -6.81 (fail) |
| 34 | Power Transformers | EURUSD | 82 | 82 | 30.5 | 0.86 | -0.48 | 0.9 | FAIL | 1.90 |
| 35 | HVDC Converters | EURSEK | 82 | 82 | 32.9 | 0.97 | -0.09 | 0.5 | FAIL | 6.62 |
| 36 | Skilled Labor | - | - | - | - | - | - | - | error: no Pepperstone instrument mapped | - |
| 37 | Cloud Concentration | QQQ.US | 82 | 82 | 28.0 | 0.77 | -0.82 | 1.1 | FAIL | 1.77 |
| 38 | Copper | COPPER | 82 | 82 | 32.9 | 0.97 | -0.10 | 0.5 | FAIL | 5.52 |
| 39 | Sand | VMC.US | 82 | 82 | 37.8 | 1.19 | 0.55 | 0.4 | FAIL | -8.33 (fail) |
| 40 | Polysilicon | USDCNH | 82 | 82 | 26.8 | 0.72 | -1.01 | 1.1 | FAIL | 1.98 |

## 4. A/B testing scaffold (9.5) — exercised

- Baseline `baseline_score0.5` vs candidate `candidate_score0.75`, 4 folds, paired per-fold Sharpe
- Full-run trades: baseline 63, candidate 32
- Mean fold Sharpe diff -3.840, t=-9.32, p~0.000 (normal approximation), folds used 4
- Decision: **keep_baseline** (candidate mean fold Sharpe not above baseline)

## 5. Signal quality tracking (9.2) and degradation detection (9.4) — exercised

- Persisted 10 monthly (month, inefficiency) rows to the SQLite signal_quality schema from synthetic replays; sample row: {'month': '2025-01', 'inefficiency_id': 1, 'signals_fired': 47, 'signals_confirmed': 47, 'trades_taken': 46, 'wins': 19, 'gross_pnl': 52.95111486130026}
- DegradationDetector over all synthetic trades: 36 inefficiencies evaluated, 34 escalations (ladder ok -> reduce_size -> paused -> retired; escalations require >= 20 closed trades in a 30-day window AND win rate < 40% or Sharpe < 0).

## 6. Data availability — what can actually be tested

- Real historical MT5 bars in this workspace: **0 instruments**. The historical-data download is owned by the CTO task; it has not landed in this workspace yet, so **no inefficiency can be acceptance-tested on real data at this time** (0/40).
- Synthetic: 36/40 inefficiencies exercisable for harness validation (4 have no Pepperstone instrument mapped: Vanilla, Palm Oil, Natural Rubber, Skilled Labor).
- EVENT / SENTIMENT / DATA triggers: no historical GDELT/Quandl replay exists yet — only PRICE-trigger plumbing is validated.

## 7. Statistical blind spots (honest limitations)

1. Synthetic prices are deterministic (trend + cycle + LCG noise): any acceptance pass is by construction, not evidence of edge.
2. One regime only. No bear markets, chop, or vol clustering; drawdown and Sharpe values are not representative of live data.
3. Execution model: flat 0.02% spread, no slippage, no swap/funding, no weekend gaps; intrabar SL/TP ambiguity is resolved stop-first (conservative) but is still an approximation.
4. Sharpe annualization (sqrt(252)) assumes independent period returns; hourly equity samples overlap, so synthetic Sharpe is overstated.
5. min_trades=30 is a weak sample: at a 48% true win rate the 95% binomial CI on 30 trades is roughly +/-17.9pp — a 30-trade pass cannot statistically separate 48% from 30%.
6. Walk-forward WFER uses ~16 windows of only 62 test bars each; segment Sharpes are extremely noisy and WFER can pass because in-sample Sharpe is low rather than out-of-sample Sharpe is high.
7. Layer-2 confirmation runs with relaxed synthetic parameters (RSI(5), SMA 5/20, min_score 0.5), not production defaults (RSI(14), SMA 50/200) — confirmation behavior on real data is untested.
8. One instrument per inefficiency (primary symbol only): correlation and portfolio-level effects are untested.
9. A/B p-value uses a normal approximation with 4 folds — advisory only; real comparisons need far more folds/data.

## 8. Verdict

- Harness: functional end-to-end (replay, metrics, acceptance gate, walk-forward, quality tracking, degradation ladder, A/B scaffold) with the full pytest suite green.
- Edge: **unproven for all 40 inefficiencies** — no out-of-sample REAL data has been tested.
- Recommendation: paper mode only. Nothing here justifies live deployment. Real-data acceptance (>=30 trades OOS, maxDD <=12%, Sharpe >=1.0, WR >=48%, PF >=1.3, WFER >=0.5) must pass before any live recommendation is made.