//+------------------------------------------------------------------+
//| Algo07_FadeM5_MRG.mq5                                           |
//| Portfolio Algo #7 — Fade M5 with Mean Reversion Gate             |
//|                                                                  |
//| STRATEGY: Fade (sell after up-spike, buy after down-spike) with  |
//| a mean reversion gate. Only enters trades when price is at       |
//| Bollinger Band extremes (BB position < 0.2 or > 0.8), meaning   |
//| the price has already extended significantly and is likely to     |
//| revert. This filters out spikes in the middle of the range.      |
//|                                                                  |
//| MULTI-PAIR TRADING: This EA trades ALL pairs affected by an      |
//| economic event, not just the chart it is attached to. A USD      |
//| event triggers trades on EURUSD, GBPUSD, USDJPY, USDCHF,        |
//| AUDUSD, NZDUSD, USDCAD simultaneously. An EUR event triggers     |
//| trades on EURUSD, EURGBP, EURJPY, EURCHF, EURAUD.               |
//|                                                                  |
//| CHART SETUP: Attach to any chart with M5 timeframe.              |
//| The EA reads data from all 14 pairs via iClose/iRSI/etc.         |
//|                                                                  |
//| PARAMETERS:                                                      |
//|   SL: 25 pips | TP: 100 pips | Spike threshold: 20 pips         |
//|   Filters: Mean reversion gate (BB position at extremes)         |
//|   MagicNumber: 461007                                            |
//|                                                                  |
//| BACKTEST RESULTS (2023-2025):                                    |
//|   261 trades | 50.2% win rate | PF 2.95 | Sharpe 6.74            |
//|   Total PnL: +5,243 pips                                         |
//+------------------------------------------------------------------+
#property copyright "USO-461/462 Portfolio"
#property version   "1.00"
#property strict

#include <NewsTraderFramework.mqh>

input int    InpMagicNumber    = 461007;    // Magic number (unique per EA)
input double InpLotSize        = 0.01;      // Lot size per trade (fallback)
input double InpNotionalEUR    = 1000.0;    // Target notional per trade in EUR (0 = use fixed lot)
input double InpSpikeThreshold = 20.0;      // Min spike in pips to trigger
input double InpSLPips         = 25.0;      // Stop loss in pips
input double InpTPPips         = 100.0;     // Take profit in pips

class CAlgo07 : public CNewsTraderBase
{
public:
   bool Setup(int magic, double lots, double notional_eur)
   {
      m_sl_pips          = InpSLPips;
      m_tp_pips          = InpTPPips;
      m_spike_threshold  = InpSpikeThreshold;
      m_lot_size         = lots;
      m_notional_eur     = notional_eur;
      m_timeframe        = PERIOD_M5;

      // Mean reversion gate: only trade at BB extremes
      m_use_mean_rev_gate = true;

      return Initialize(magic, "Algo07_FadeM5_MRG");
   }
};

CAlgo07 algo;

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
