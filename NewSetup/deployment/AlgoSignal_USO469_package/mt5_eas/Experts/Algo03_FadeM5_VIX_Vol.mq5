//+------------------------------------------------------------------+
//| Algo03_FadeM5_VIX_Vol.mq5                                       |
//| Portfolio Algo #3 — Fade M5 with VIX + Volume filters            |
//|                                                                  |
//| STRATEGY: Fades the post-event spike on M5, but only in calm     |
//| markets (VIX < 18) with high volume confirmation (ratio > 2.0).  |
//| The low-VIX filter ensures mean reversion works (trending/panic  |
//| markets break the fade). High volume confirms real participation. |
//|                                                                  |
//| PARAMETERS:                                                      |
//|   - Timeframe: M5                                                |
//|   - SL: 15 pips, TP: 100 pips                                   |
//|   - Spike threshold: 10 pips (lower, filtered by VIX+Vol)        |
//|   - Filters: VIX < 18, Volume ratio > 2.0                       |
//|   - Backtest expectancy: +27.85 pips/trade (best in portfolio)   |
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
input double   InpLotSize         = 0.01;  // Lot size per trade (fallback)
input double   InpNotionalEUR     = 1000.0;// Target notional per trade in EUR (0 = use fixed lot)
input int      InpMagicNumber     = 461003;// Magic number (unique per EA)
input double   InpSLPips          = 15;    // Stop loss in pips
input double   InpTPPips          = 100;   // Take profit in pips
input double   InpSpikeThreshold  = 10;    // Minimum spike in pips to trigger
input double   InpVIXThreshold    = 18;    // Maximum VIX level (calm markets)
input double   InpVolumeThreshold = 2.0;   // Minimum volume ratio

//--- EA instance
class CAlgo03 : public CNewsTraderBase
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

      // VIX filter: only trade in calm markets
      m_use_vix_filter    = true;
      m_vix_below         = true;         // Require VIX BELOW threshold
      m_vix_threshold     = InpVIXThreshold;

      // Volume filter: only trade on volume spikes
      m_use_volume_filter = true;
      m_volume_above      = true;
      m_volume_threshold  = InpVolumeThreshold;

      return Initialize(magic, "Algo03_FadeM5_VIX_Vol");
   }
};

CAlgo03 trader;

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
