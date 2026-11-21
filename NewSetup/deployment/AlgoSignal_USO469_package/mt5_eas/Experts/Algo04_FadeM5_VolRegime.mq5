//+------------------------------------------------------------------+
//| Algo04_FadeM5_VolRegime.mq5                                     |
//| Portfolio Algo #4 — Fade M5 with Volatility Regime filter        |
//|                                                                  |
//| STRATEGY: Fades the post-event spike on M5, but only during      |
//| high-volatility regimes (ATR in top 33rd percentile over 100     |
//| bars). High-vol environments produce larger overreactions that    |
//| are more likely to revert.                                       |
//|                                                                  |
//| PARAMETERS:                                                      |
//|   - Timeframe: M5                                                |
//|   - SL: 25 pips, TP: 60 pips (balanced R:R)                     |
//|   - Spike threshold: 15 pips                                     |
//|   - Filter: ATR percentile > 0.67 (high volatility regime)       |
//|   - Backtest trades: 545, PnL: +8,214 pips                      |
//|                                                                  |
//| MULTI-PAIR OPERATION:                                            |
//| This EA trades ALL pairs affected by the triggering event's      |
//| currency. Attach it to ANY M5 chart (e.g. EURUSD M5). When a    |
//| USD event fires, it opens trades on EURUSD, GBPUSD, USDJPY,     |
//| USDCHF, AUDUSD, NZDUSD, USDCAD. When an EUR event fires, it    |
//| trades EURUSD, EURGBP, EURJPY, EURCHF, EURAUD. And so on for    |
//| GBP, JPY, CHF, AUD, NZD, CAD events.                            |
//|                                                                  |
//| HOW TO ADD TO CHART:                                             |
//| 1. Open any M5 chart (EURUSD recommended as anchor)              |
//| 2. Drag this EA onto the chart from the Navigator panel           |
//| 3. In the Inputs tab, set LotSize for your account               |
//| 4. Enable "Allow Algo Trading" and "Allow live trading"          |
//| 5. Only ONE instance needed — it handles all 14 pairs            |
//+------------------------------------------------------------------+
#property copyright "USO-461/462 Portfolio"
#property version   "1.00"
#property strict

#include <NewsTraderFramework.mqh>

//--- Input parameters
input double   InpLotSize        = 0.01;   // Lot size per trade (fallback)
input double   InpNotionalEUR    = 1000.0; // Target notional per trade in EUR (0 = use fixed lot)
input int      InpMagicNumber    = 461004; // Magic number (unique per EA)
input double   InpSLPips         = 25;     // Stop loss in pips
input double   InpTPPips         = 60;     // Take profit in pips
input double   InpSpikeThreshold = 15;     // Minimum spike in pips to trigger

//--- EA instance
class CAlgo04 : public CNewsTraderBase
{
public:
   bool Setup(int magic, double lots, double notional_eur)
   {
      m_sl_pips           = InpSLPips;
      m_tp_pips           = InpTPPips;
      m_spike_threshold   = InpSpikeThreshold;
      m_lot_size          = lots;
      m_notional_eur      = notional_eur;
      m_timeframe         = PERIOD_M5;

      // Volatility regime filter: only trade during high-vol periods
      m_use_vol_regime    = true;
      m_vol_regime_target = "high_only";   // ATR percentile > 0.67

      return Initialize(magic, "Algo04_FadeM5_VolRegime");
   }
};

CAlgo04 trader;

//+------------------------------------------------------------------+
int OnInit()
{
   if(!trader.Setup(InpMagicNumber, InpLotSize, InpNotionalEUR))
      return INIT_FAILED;
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnTick()
{
   trader.OnTickHandler();
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   trader.Cleanup();
}
//+------------------------------------------------------------------+
