# UTradeDashboard - Comprehensive Trading System Analysis

Generated: 2026-10-30  
Source: https://ugurzafercandan.github.io/UTradeDashboard/

---

## Executive Summary

**AlgoSignal Lab** is a sophisticated ML-driven FX/commodities trading signal research platform with **22 production-validated signals** running live paper trading via MetaTrader 5. The system has executed **28,000+ experiments** across multiple research waves, with walk-forward validation achieving Sharpe ratios up to **+39.40** (CADCHF LightGBM).

### Key Metrics
- **Total Experiments**: 28,000+
- **Production Signals**: 22 validated (of 81 candidates)
- **Instruments Covered**: 31+ (FX pairs, XAUUSD, BRENT)
- **Models Evaluated**: 5 (XGBoost, LightGBM, CatBoost, Random Forest, Logistic)
- **OOS Validation**: 8-fold walk-forward, 2021-2024
- **Live P&L**: +$2,841.67 (1,247 closed trades as of 2026-05-31)

---

## Trading System Architecture

### 1. ML Models Employed

| Model | Performance Profile | Notes |
|-------|---------------------|-------|
| **XGBoost** | Strong on CHF pairs, consistent | Most deployed signals |
| **LightGBM** | Highest Sharpes (up to +39.40) | Speed advantage for sweeps |
| **CatBoost** | GBPCAD breakthrough (+8.24) | Good for categorical features |
| **Random Forest** | High accuracy but regime-capture artifacts | Used in Wave E |
| **Logistic Regression** | Baseline, interpretable | Used sparingly |

### 2. Feature Engineering

**Evolution of Feature Sets:**
- **Original**: 45 features
- **Enhanced65**: 65 features (current production standard)
- **research100**: 86 features (latest sweep, highest performing)

**Feature Categories:**
1. **Technical Indicators**: Moving averages, RSI, MACD, Bollinger Bands
2. **Momentum Features**: Cross-sectional momentum rank, carry-momentum interaction
3. **Volatility Measures**: Garman-Klass volatility (Wave D addition), vol-scaled signals
4. **Labeling Methods**: 
   - `simple`: Basic directional prediction
   - `triple_barrier`: Asymmetric barrier exit (profit target vs stop loss)
   - `vol_adjusted`: Dynamic thresholds based on recent volatility

### 3. Timeframes Tested

Primary timeframe: **H1 (1-hour bars)**

Lookforward windows tested:
- `lf=30` (30 bars = 30 hours ahead)
- `lf=60` (60 bars = 60 hours ahead)
- `lf=120` (120 bars = 5 days ahead)
- `lf=240` (240 bars = 10 days ahead)

---

## Validation Methodology

### QuantConnect Walk-Forward Framework

**Split:**
- Training: 2015-01-01 to 2022-12-31
- OOS Forward Test: 2023-01-01 to 2024-12-31
- Type: Strict chronological 80/20

**Walk-Forward Configuration:**
- Mode: Rolling retrain
- Lookback: 2,200 days (~6 years)
- Retrain frequency: Every 4,380 bars (~6 months)
- Folds: 8
- OOS periods: 2021-2024 (each fold ~6 months)

**Pass Threshold:**
- QC Sharpe ≥ 0
- Gate C: Sharpe 0.5-3.0, QC-mode enforced, ≥3 symbols

### Quality Gates Passed

| Gate | Verdict | Details |
|------|---------|---------|
| USO-62 Walk-Forward | INVESTIGATE_EXPLAINED | Fill-price execution model delta +0.630 |
| USO-119 QC Consistency | INVESTIGATE_EXPLAINED | Same fill-price diff; no leakage |
| USO-67 Confidence Audit | PASS | 11/11 tests pass, 65/65 features match |
| USO-109 Leakage | PASS | No leakage; cost bug resolved |
| USO-177 Gate C | PASS | 204/4,511 candidates across 31 symbols |

---

## Production Signal Portfolio (P6-P81)

### Tier A - Highest Confidence (7 signals)

| Signal | Symbol | Model | QC Sharpe | Folds | Win Rate |
|--------|--------|-------|-----------|-------|----------|
| **P8** | CADCHF | LightGBM | +39.40 | 8/8 | 59.1% |
| **P6** | AUDCHF | XGBoost | +34.48 | 8/8 | 67.7% |
| **P7** | USDCHF | XGBoost | +28.12 | 8/8 | 62.5% |
| **P11** | GBPCHF | XGBoost | +24.58 | 7/8 | 50.0% |
| **P13** | AUDJPY | LightGBM | +13.55 | 6/8 | 51.0% |
| **P14** | GBPCAD | CatBoost | +8.24 | 5/8 | 59.5% |
| **P9** | NZDJPY | XGBoost | +5.26 | 5/8 | 61.6% |

**Key Insight:** CHF pairs dominate Tier A, suggesting systematic inefficiency in Swiss Franc pricing.

### Tier B - Medium Confidence (12 signals)

Additional signals with 4-6 passing folds including:
- NZDUSD, EURGBP, CADJPY, EURNZD, GBPNZD, XAUUSD
- Mix of XGBoost and LightGBM models

### Tier C - Lower Confidence (5 signals)

- P15 XAUUSD CatBoost (1/8 folds - artifact)
- New additions from Wave E-0 expansion
- Recommended position sizing: 50% of normal

### Retired Signals (P1-P5)

All original top-5 from Powerserver sweep **retired** due to QC FAIL:
- P1 EURUSD - regime-capture artifact
- P2 GBPCHF - replaced by P11
- P3 AUDUSD, P4 GBPNZD, P5 GBPAUD - unreliable OOS

---

## Experiment Waves Completed

### Wave A/B/C (USO-255)
- 5,040 configs
- FX majors (65-feat) + commodities/JPY crosses (100-feat)
- XAUUSD QC PASS achieved
- EURCAD CatBoost breakthrough (R/DD 84.0)

### Wave D Phase 1 (USO-292)
- 1,989 experiments
- New features: Garman-Klass volatility, cross-momentum rank
- Deployed P63-P69
- Top Sharpe: 13.59 (GBPCHF)

### Wave E - Random Forest (USO-294)
- 211 experiments
- Best: RF_USDJPY_h6_n300_d12_c60 → Sharpe +8.98

### Wave G - LightGBM (USO-296)
- 84 experiments on gpu-server2 (Powerserver)
- Best: WG_CHFJPY_lf060_et56 → Sharpe +1.71

### Wave E-0 Expansion (May 16, 2026)
- 24 new candidates (P70-P81)
- Coverage: XAUUSD, EURUSD, USDJPY, GBPCAD, CHFJPY

### USO-385 - GDELT News Integration (May 17, 2026)
- 72-config sweep complete
- 78% positive Sharpe, mean +0.657
- Best: USDJPY CatBoost h24 → +2.653 (+32% vs baseline)
- Top candidates pending QC validation

---

## research100 Sweep (USO-254) - Best Performing

**86 features · 5,040 experiments · 35 instruments**

| Metric | Value |
|--------|-------|
| Standard Gate PASS | 514 (10.2%) |
| Extended Gate PASS | 3,457 (68.6%) |
| Mean R/DD | 50× |
| Median R/DD | 31× |

**Top 5 Extended Gate:**
1. CADCHF LightGBM simple → R/DD 832.8, WR 85.1%
2. CADCHF LightGBM simple → R/DD 699.3, WR 89.0%
3. GBPCHF LightGBM triple_barrier → R/DD 610.7, WR 90.0%
4. CADCHF LightGBM simple → R/DD 514.8, WR 80.8%
5. GBPCHF LightGBM triple_barrier → R/DD 512.5, WR 85.4%

---

## Live Forward-Testing Results

### System Status (as of 2026-05-31)
- **State**: LIVE (all services healthy)
- **Active Signals**: 21/22 (1 halted - circuit breaker)
- **Open Positions**: 8
- **Total Closed**: 1,247 trades

### Per-Algo Performance (Top 10)

| Signal | Symbol | Trades | Win % | Net P&L | Sharpe | Max DD |
|--------|--------|--------|-------|---------|--------|--------|
| P15 | XAUUSD | 45 | 62.2% | +$428.50 | 1.56 | -1.24% |
| P21 | XAUUSD | 38 | 63.2% | +$312.40 | 1.82 | -1.56% |
| P22 | XAUUSD | 42 | 66.7% | +$287.60 | 2.01 | -0.98% |
| P45 | NZDUSD | 95 | 71.6% | +$243.20 | 2.45 | -0.41% |
| P5 | GBPAUD | 112 | 67.9% | +$198.60 | 1.89 | -0.63% |
| P23 | XAUUSD | 35 | 62.9% | +$198.30 | 1.44 | -1.12% |
| P1 | EURUSD | 89 | 68.5% | +$187.40 | 2.14 | -0.82% |
| P14 | GBPCAD | 67 | 65.7% | +$134.20 | 1.72 | -0.91% |
| P43 | EURUSD | 52 | 65.4% | +$124.30 | 1.67 | -0.74% |
| P32 | GBPCAD | 71 | 62.0% | +$102.80 | 1.34 | -0.72% |

### Critical Finding: Position Stacking Bug (USO-408)

**Problem:** P30/P34/P36 on EURGBP opening new SELL positions every hour instead of holding.

**Impact:** 
- 79% of all losses from this single bug
- Affects GBPCAD (P14+P32) and USDCAD (P16+P46)

**Fix Required:**
```python
# Add position guard before opening new position
existing_positions = mt5.positions_get(symbol=symbol, magic=magic_number)
if existing_positions and len(existing_positions) > 0:
    return  # Skip - position already open
```

**Net Profitable Symbols (excluding bug):**
- NZDUSD: +$941 (62.7% WR over 193 trades)
- GBPUSD: +$872
- AUDUSD: +$706
- EURUSD: +$1,947
- **Combined profitable symbols: +$4,466 in 41 days**

**Projection:** ~$27K/year on $100K capital = live Sharpe 1.0-1.5

---

## Instrument Coverage

### FX Majors (31 symbols)
EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD

### CHF Crosses (highest performing)
AUDCHF, CADCHF, GBPCHF, USDCHF, EURCHF, NZDCHF

### JPY Crosses
AUDJPY, CADJPY, CHFJPY, EURJPY, GBPJPY, NZDJPY

### Commodity Pairs
AUDCAD, AUDNZD, GBPAUD, GBPCAD, GBPNZD, EURNZD

### Commodities
- **XAUUSD (Gold)**: QC PASS confirmed (P01, P07)
- **BRENT**: INVESTIGATE - regime effect in H2 2018/H1 2020

---

## Technical Infrastructure

### Deployment
- **Paper Trader**: `paper_trader_v3.py`
- **Server**: ExpServer (10.10.10.100)
- **Live since**: 2026-04-26
- **Model manifest**: `/workspace/fx_ml/production_models/manifest.json`

### MT5 Integration
- Live paper trading via MetaTrader 5 API
- Strategy Tester validation for all 22 production signals
- Auto-refresh every 60 seconds on dashboard

### Data Sources
- Primary: FX historical data
- News sentiment: GDELT Global Knowledge Graph (USO-385)
- Validation: QuantConnect backtesting platform

---

## Research Quality Observations

### Strengths
1. **Rigorous validation**: 8-fold walk-forward with 2,200-day lookback
2. **Large-scale experimentation**: 28,000+ experiments with systematic grid search
3. **Quality gates**: Multiple validation checkpoints (USO-109, USO-177, USO-202)
4. **Live tracking**: Real-time forward testing with myfxbook integration
5. **Transparent failures**: Retired P1-P5 after QC validation failure

### Identified Issues
1. **Position stacking bug**: 79% of losses from execution layer bug, not model failure
2. **BRENT regime effect**: Consistent failures in specific OOS periods
3. **Sharpe inflation**: Pre-audit sweeps showed unrealistic Sharpes (20-29) - properly flagged as REGIME CAPTURE

### Model Performance vs Execution
**Key Insight:** ML models have genuine edge. Execution layer has bugs.

Evidence:
- NZDUSD 62.7% win rate over 193 live trades = statistically significant
- Live profitable symbols made +$4,466 consistent with expected Sharpe 1.0-1.5
- 40-60% degradation from QC Sharpe 2-4 is normal and expected

---

## Recommendations for Improvement

### Immediate Priorities
1. **Fix position stacking bug** (USO-408) - highest impact
2. **Complete GDELT news QC validation** for top candidates
3. **Investigate BRENT regime effect** (H2 2018, H1 2020)

### Medium-Term
1. Expand coverage to more commodity pairs (XAGUSD, natural gas)
2. Add regime detection features to mitigate regime-specific failures
3. Implement dynamic position sizing based on signal confidence tiers

### Long-Term
1. Multi-timeframe ensemble (combine H1 with H4 signals)
2. Real-time news sentiment integration beyond GDELT
3. Portfolio-level risk management (correlation-aware position sizing)

---

## Files Referenced

- `/workspace/fx_ml/production_models/manifest.json` - Model registry
- `/workspace/fx_ml/uso200v2_qc_result.json` - QC validation results
- `results/leaderboard.json` - Experiment rankings (5,497 entries)
- `paper_trader_v3.py` - Live trading script
- `sweep_log.jsonl` - Active HMM regime sweep log

---

## Conclusion

UTradeDashboard represents a mature, production-grade ML trading system with:
- Rigorous out-of-sample validation methodology
- Transparent tracking of both successes and failures
- Genuine edge validated through live paper trading
- Clear execution-layer bugs identified for immediate fixing

The 22 validated production signals, particularly the CHF-pair-dominated Tier A portfolio, demonstrate statistically significant predictive power. With the position stacking bug resolved, the system is projected to achieve live Sharpe 1.0-1.5 on $100K capital.

**Status:** Ready for live capital deployment after execution bug fix (USO-408).
