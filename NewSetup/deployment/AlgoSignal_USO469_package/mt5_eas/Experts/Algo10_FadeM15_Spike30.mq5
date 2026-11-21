//+------------------------------------------------------------------+
//| Algo10_FadeM15_Spike30.mq5                                      |
//| Portfolio Algo #10 — Fade M15 Baseline (Spike > 30)              |
//|                                                                  |
//| STRATEGY: Fade (sell after up-spike, buy after down-spike) on    |
//| M15 timeframe. This is a baseline algo with NO additional        |
//| filters — it relies purely on spike size (> 30 pips) to identify |
//| overreactions to economic events. The M15 timeframe gives the    |
//| trade more room to develop compared to M5.                       |
//|                                                                  |
//| This algo is the highest-volume producer in the portfolio (1,092 |
//| trades in backtest) because it applies no filters beyond spike   |
//| size, capturing every significant news move for mean reversion.  |
//|                                                                  |
//| MULTI-PAIR TRADING: This EA trades ALL pairs affected by an      |
//| economic event, not just the chart it is attached to. A USD      |
//| event triggers trades on EURUSD, GBPUSD, USDJPY, USDCHF,        |
//| AUDUSD, NZDUSD, USDCAD simultaneously. An EUR event triggers     |
//| trades on EURUSD, EURGBP, EURJPY, EURCHF, EURAUD.               |
//|                                                                  |
//| CHART SETUP: Attach to any chart with M15 timeframe.             |
//| The EA reads data from all 14 pairs via iClose/iRSI/etc.         |
//|                                                                  |
//| PARAMETERS:                                                      |
//|   SL: 15 pips | TP: 60 pips | Spike threshold: 30 pips          |
//|   Filters: None (baseline)                                       |
//|   MagicNumber: 461010                                            |
//|                                                                  |
//| BACKTEST RESULTS (2023-2025):                                    |
//|   1,092 trades | 52.8% win rate | PF 3.30 | Sharpe 7.53          |
//|   Total PnL: +14,948 pips                                        |
//+------------------------------------------------------------------+
#property copyright "USO-461/462 Portfolio"
#property version   "1.00"
#property strict

#include <NewsTraderFramework.mqh>

input int    InpMagicNumber    = 461010;    // Magic number (unique per EA)
input double InpLotSize        = 0.01;      // Lot size per trade (fallback)
input double InpNotionalEUR    = 1000.0;    // Target notional per trade in EUR (0 = use fixed lot)
input double InpSpikeThreshold = 30.0;      // Min spike in pips to trigger
input double InpSLPips         = 15.0;      // Stop loss in pips
input double InpTPPips         = 60.0;      // Take profit in pips

class CAlgo10 : public CNewsTraderBase
{
public:
   bool Setup(int magic, double lots, double notional_eur)
   {
      m_sl_pips          = InpSLPips;
      m_tp_pips          = InpTPPips;
      m_spike_threshold  = InpSpikeThreshold;
      m_lot_size         = lots;
      m_notional_eur     = notional_eur;
      m_timeframe        = PERIOD_M15;

      // Baseline: no additional filters
      return Initialize(magic, "Algo10_FadeM15_Spike30");
   }
};

CAlgo10 algo;

int OnInit()
{
   if(!algo.Setup(InpMagicNumber, InpLotSize, InpNotionalEUR))
      return INIT_FAILED;
   return INIT_SUCCEEDED;
}

void OnTick()
{
   algo.OnTickHandler();
}

void OnDeinit(const int reason)
{
   algo.Cleanup();
}
