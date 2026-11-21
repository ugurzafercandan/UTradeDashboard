# News Event Portfolio — MT5 Expert Advisors

## Overview

This directory contains 10 Expert Advisors (EAs) that implement a diversified news-event 
trading portfolio. The portfolio was selected from a 21,588-config ML sweep using Forex 
Factory calendar data (2023-2025), optimized for diversification via greedy forward 
selection with a cosine-similarity penalty.

**Combined backtest performance:** +78,683 pips | Avg Sharpe 8.90 | Avg PF 4.15

## How These EAs Trade Multiple Pairs

**These are event-driven EAs, not chart-specific EAs.**

Each EA is attached to ONE chart but automatically trades ALL currency pairs affected by 
the triggering economic event. The EA reads the MT5 built-in economic calendar and, when 
a high/medium-impact event is released:

1. Identifies the event's currency (e.g., USD for NFP, EUR for ECB rate decision)
2. Looks up all affected pairs via the currency→pair mapping:

   | Currency | Pairs Traded |
   |----------|-------------|
   | USD | EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, USDCAD |
   | EUR | EURUSD, EURGBP, EURJPY, EURCHF, EURAUD |
   | GBP | GBPUSD, EURGBP, GBPJPY, GBPCHF |
   | JPY | USDJPY, EURJPY, GBPJPY, AUDJPY |
   | CHF | USDCHF, EURCHF, GBPCHF |
   | AUD | AUDUSD, EURAUD, AUDJPY |
   | NZD | NZDUSD |
   | CAD | USDCAD |

3. Measures the post-event price spike on each pair
4. If the spike exceeds the threshold and all filters pass, opens a trade

**You do NOT need to attach the EA to each pair's chart.** One instance on any chart 
handles all 14 pairs. The EA uses `iClose()`, `iRSI()`, etc. with explicit symbol 
parameters to read remote pair data.

## Directory Structure

```
mt5_eas/
├── Include/
│   └── NewsTraderFramework.mqh    ← Shared framework (calendar, indicators, trade mgmt)
├── Experts/
│   ├── Algo01_BBBreakout_H1.mq5   ← BB breakout, VIX>22, high volume
│   ├── Algo02_FadeM5_Spike30.mq5  ← Baseline fade, spike>30 pips
│   ├── Algo03_FadeM5_VIX_Vol.mq5  ← Fade, VIX<18, high volume
│   ├── Algo04_FadeM5_VolRegime.mq5 ← Fade, high volatility regime only
│   ├── Algo05_FadeM15_VIX_LowVol.mq5 ← Fade M15, VIX<18, low volume
│   ├── Algo06_MACDFade_Gold.mq5   ← MACD-confirmed fade, negative gold corr
│   ├── Algo07_FadeM5_MRG.mq5      ← Fade with mean reversion gate
│   ├── Algo08_FadeM5_VolFilter.mq5 ← Fade, low volume filter
│   ├── Algo09_FadeM5_VIX.mq5      ← Fade, VIX<18
│   └── Algo10_FadeM15_Spike30.mq5 ← Baseline fade M15
└── README.md                       ← This file
```

## Installation

### Step 1: Copy Files to MT5 Data Folder

Open your MT5 terminal, then go to **File → Open Data Folder**. This opens the 
`MQL5` directory. Copy the files:

```
MQL5/
├── Include/
│   └── NewsTraderFramework.mqh     ← Copy from mt5_eas/Include/
└── Experts/
    └── NewsPortfolio/              ← Create this folder
        ├── Algo01_BBBreakout_H1.mq5
        ├── Algo02_FadeM5_Spike30.mq5
        ├── ...all 10 .mq5 files
        └── Algo10_FadeM15_Spike30.mq5
```

### Step 2: Compile the EAs

In MT5, open **MetaEditor** (F4 or click the MetaEditor icon):

1. In the Navigator panel, expand `Experts > NewsPortfolio`
2. Double-click each `.mq5` file to open it
3. Press **F7** (Compile) for each one
4. Check the **Errors** tab — should show 0 errors
5. The compiled `.ex5` files will appear in the same directory

Alternatively, compile all from command line:
```
"C:\Program Files\MetaTrader 5\metaeditor64.exe" /compile:"MQL5\Experts\NewsPortfolio\Algo01_BBBreakout_H1.mq5"
```

### Step 3: Enable Algo Trading

In MT5 terminal:
1. Go to **Tools → Options → Expert Advisors**
2. Check **"Allow algorithmic trading"**
3. Check **"Allow DLL imports"** (not required for these EAs, but often needed)
4. Click OK

### Step 4: Attach EAs to Charts

**IMPORTANT: Chart timeframe must match the EA's designed timeframe.**

Open charts and attach each EA:

| EA | Attach to Chart | Timeframe |
|----|----------------|-----------|
| Algo01_BBBreakout_H1 | Any pair (e.g. EURUSD) | **H1** |
| Algo02_FadeM5_Spike30 | Any pair (e.g. EURUSD) | **M5** |
| Algo03_FadeM5_VIX_Vol | Any pair (e.g. EURUSD) | **M5** |
| Algo04_FadeM5_VolRegime | Any pair (e.g. EURUSD) | **M5** |
| Algo05_FadeM15_VIX_LowVol | Any pair (e.g. EURUSD) | **M15** |
| Algo06_MACDFade_Gold | Any pair (e.g. EURUSD) | **M5** |
| Algo07_FadeM5_MRG | Any pair (e.g. EURUSD) | **M5** |
| Algo08_FadeM5_VolFilter | Any pair (e.g. EURUSD) | **M5** |
| Algo09_FadeM5_VIX | Any pair (e.g. EURUSD) | **M5** |
| Algo10_FadeM15_Spike30 | Any pair (e.g. EURUSD) | **M15** |

To attach:
1. Open a chart (e.g., right-click any symbol in Market Watch → Chart Window)
2. Set the timeframe (M5, M15, or H1 toolbar buttons)
3. In the Navigator panel (Ctrl+N), expand **Expert Advisors > NewsPortfolio**
4. Drag the EA onto the chart
5. In the popup dialog:
   - **Common tab**: Check "Allow algo trading"
   - **Inputs tab**: Adjust `LotSize` if needed (default 0.01)
6. Click OK

The smiley face icon in the top-right of the chart confirms the EA is running.

**You only need 10 charts total** — one per EA. The chart's pair doesn't matter since 
each EA trades all affected pairs. However, attaching to the most liquid pair (EURUSD) 
ensures frequent tick updates to trigger the OnTick handler.

### Running All 10 EAs Simultaneously

For the full portfolio:
1. Open 10 charts (Ctrl+N → right-click EURUSD → Chart Window, repeat 10 times)
2. Set timeframes: 7 charts to M5, 2 charts to M15, 1 chart to H1
3. Attach one EA to each chart
4. Each EA uses a unique MagicNumber (461001-461010) so trades don't interfere

**Tip:** Use MT5 Profiles to save this chart layout. Go to **File → Profiles → Save As** 
and name it "NewsPortfolio". You can restore it anytime with **File → Profiles → NewsPortfolio**.

## Backtesting with Strategy Tester

### Single EA Backtest

1. Open Strategy Tester (Ctrl+R)
2. Select the EA from the dropdown
3. Set the symbol to any pair (EURUSD recommended)
4. Set the timeframe to match the EA (M5, M15, or H1)
5. Set the date range: 2023-01-01 to 2025-01-01
6. Modeling: **Every tick based on real ticks** (most accurate) or **OHLC on M1**
7. Click **Start**

**Note on multi-pair backtesting:** MT5 Strategy Tester runs on a single symbol. The EA 
will still attempt to read other symbols' data via `iClose()` etc., which works in the 
tester if those symbols have history loaded. Before running:
- Ensure all 14 pairs have history data (go to Market Watch → Symbols → download history for each)

### Optimization

For parameter optimization:
1. In Strategy Tester, click the **Inputs** tab
2. Adjust `LotSize`, and the EA will re-run with different values
3. Use **Slow complete algorithm** for exhaustive search

## EA Summary Table

| # | EA File | Strategy | TF | SL | TP | Spike | Filters | Magic | Backtest PnL |
|---|---------|----------|-----|-----|-----|-------|---------|-------|-------------|
| 1 | Algo01_BBBreakout_H1 | BB Breakout | H1 | 60 | 20 | — | VIX>22, Vol>2.0 | 461001 | +340 pips |
| 2 | Algo02_FadeM5_Spike30 | Fade | M5 | 15 | 100 | >30 | None | 461002 | +16,522 pips |
| 3 | Algo03_FadeM5_VIX_Vol | Fade | M5 | 15 | 100 | >10 | VIX<18, Vol>2.0 | 461003 | +2,200 pips |
| 4 | Algo04_FadeM5_VolRegime | Fade | M5 | 25 | 60 | >15 | Vol regime high | 461004 | +8,214 pips |
| 5 | Algo05_FadeM15_VIX_LowVol | Fade | M15 | 15 | 60 | >30 | VIX<18, Vol<0.5 | 461005 | +3,160 pips |
| 6 | Algo06_MACDFade_Gold | MACD Fade | M5 | 15 | 100 | >10 | Gold corr neg | 461006 | +11,141 pips |
| 7 | Algo07_FadeM5_MRG | Fade + MRG | M5 | 25 | 100 | >20 | Mean rev gate | 461007 | +5,243 pips |
| 8 | Algo08_FadeM5_VolFilter | Fade | M5 | 15 | 40 | >15 | Vol<0.5 | 461008 | +5,521 pips |
| 9 | Algo09_FadeM5_VIX | Fade | M5 | 15 | 60 | >30 | VIX<18 | 461009 | +11,393 pips |
| 10 | Algo10_FadeM15_Spike30 | Fade | M15 | 15 | 60 | >30 | None | 461010 | +14,948 pips |

## How the Strategies Work

### Fade Strategy (Algos 2-5, 7-10)
After a high-impact economic event causes a sharp price spike (e.g., NFP beats expectations 
and USD spikes up), the EA trades **against** the spike direction — betting on mean reversion. 
If USD spiked UP (e.g., EURUSD dropped 30+ pips), the EA BUYS EURUSD expecting a bounce.

### BB Breakout Strategy (Algo 1)
When price breaks outside Bollinger Bands during a high-VIX, high-volume economic event, 
the EA trades **with** the breakout direction — momentum continuation.

### MACD Fade Strategy (Algo 6)
Same as fade but adds MACD histogram confirmation: only enters when MACD agrees with the 
fade direction. Additionally requires negative gold correlation (gold moving opposite to 
the pair, suggesting a risk-off/risk-on divergence).

## Important Notes

1. **Demo first.** Always run on a demo account before live trading.
2. **VIX data.** Algos 1, 3, 5, 9 use VIX data. The framework tries to find VIX on your 
   broker (common symbols: VIX, VIX.cash, VOLATILITY). If not available, it falls back to 
   an ATR-based approximation. Check your broker's symbol list.
3. **Gold data.** Algo 6 uses XAUUSD correlation. Most brokers provide XAUUSD or GOLD.
4. **Calendar data.** MT5's built-in economic calendar (`CalendarValueHistory()`) requires 
   MT5 build 2085+. Check Help → About.
5. **Lot sizing.** Default is 0.01 lots (micro). Adjust the `LotSize` input parameter.
6. **Spread consideration.** Backtested PnL doesn't account for variable spreads during 
   news events, which can widen significantly. Use limit orders or increase slippage tolerance.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| EA not trading | Check algo trading is enabled (green play button in toolbar) |
| "Symbol not found" in log | Your broker may use different symbol names (e.g., EURUSD.m). Update the pair mapping in NewsTraderFramework.mqh |
| No calendar events detected | Ensure MT5 build ≥ 2085. Check View → Calendar is populated |
| Trades only on one pair | Working as designed — it trades multiple pairs per event. Check the Experts log |
| Compile errors | Ensure NewsTraderFramework.mqh is in `MQL5/Include/` (not in Experts/) |
