//+------------------------------------------------------------------+
//| Algo08_FadeM5_VolFilter.mq5                                      |
//| Portfolio Algo #8 — Fade M5 with Low Volume Filter               |
//|                                                                  |
//| STRATEGY: Fade (sell after up-spike, buy after down-spike) that  |
//| only trades in low-volume conditions (volume ratio <= 0.5).      |
//| The idea is that spikes on thin volume are less sustainable and   |
//| more likely to revert. Uses a tighter TP (40 pips) for faster    |
//| mean-reversion captures.                                         |
//|                                                                  |
//| VOLUME FILTER: Only trades when current tick volume is at most   |
//| 50% of the 20-bar average. Spikes on low volume are often        |
//| caused by thin liquidity rather than genuine momentum.            |
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
//|   SL: 15 pips | TP: 40 pips | Spike threshold: 15 pips          |
//|   Filters: Volume ratio <= 0.5 (low volume only)                 |
//|   MagicNumber: 461008                                            |
//|                                                                  |
//| BACKTEST RESULTS (2023-2025):                                    |
//|   442 trades | 56.8% win rate | PF 3.11 | Sharpe 8.11            |
//|   Total PnL: +5,521 pips                                         |
//+------------------------------------------------------------------+
#property copyright "USO-461/462 Portfolio"
#property version   "1.00"
#property strict

#include <NewsTraderFramework.mqh>

input int    InpMagicNumber    = 461008;    // Magic number (unique per EA)
input double InpLotSize        = 0.01;      // Lot size per trade (fallback)
input double InpNotionalEUR    = 1000.0;    // Target notional per trade in EUR (0 = use fixed lot)
input double InpSpikeThreshold = 15.0;      // Min spike in pips to trigger
input double InpSLPips         = 15.0;      // Stop loss in pips
input double InpTPPips         = 40.0;      // Take profit in pips
input double InpVolThreshold   = 0.5;       // Volume ratio threshold (trade below this)

class CAlgo08 : public CNewsTraderBase
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

      // Low volume filter: skip when volume ratio > threshold
      m_use_volume_filter = true;
      m_volume_above      = false;   // false = skip when vol is ABOVE threshold
      m_volume_threshold  = InpVolThreshold;

      return Initialize(magic, "Algo08_FadeM5_VolFilter");
   }
};

CAlgo08 algo;

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
