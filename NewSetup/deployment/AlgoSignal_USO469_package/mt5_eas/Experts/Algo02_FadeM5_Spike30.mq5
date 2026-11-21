//+------------------------------------------------------------------+
//| Algo02_FadeM5_Spike30.mq5                                       |
//| Portfolio Algo #2 — Baseline Fade on M5 after 30-pip spike       |
//|                                                                  |
//| STRATEGY: Fades (trades against) the initial spike after a       |
//| high/medium-impact economic event. No additional filters — pure  |
//| mean-reversion play on the post-news overreaction.               |
//|                                                                  |
//| PARAMETERS:                                                      |
//|   - Timeframe: M5                                                |
//|   - SL: 15 pips, TP: 100 pips (asymmetric, let winners run)     |
//|   - Spike threshold: 30 pips minimum move to trigger             |
//|   - Backtest PnL: +16,522 pips (highest PnL in portfolio)        |
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
input int      InpMagicNumber    = 461002; // Magic number (unique per EA)
input double   InpSLPips         = 15;     // Stop loss in pips
input double   InpTPPips         = 100;    // Take profit in pips
input double   InpSpikeThreshold = 30;     // Minimum spike in pips to trigger

//--- EA instance
class CAlgo02 : public CNewsTraderBase
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

      // Baseline fade: no additional filters
      // All filter flags default to false in the base class

      return Initialize(magic, "Algo02_FadeM5_Spike30");
   }
};

CAlgo02 trader;

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
