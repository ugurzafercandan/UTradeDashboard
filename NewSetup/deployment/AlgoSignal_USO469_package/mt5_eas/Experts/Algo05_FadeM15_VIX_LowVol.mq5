//+------------------------------------------------------------------+
//| Algo05_FadeM15_VIX_LowVol.mq5                                   |
//| Portfolio Algo #5 — Fade M15 in calm markets with low volume     |
//|                                                                  |
//| STRATEGY: Fades the post-event spike on M15, targeting calm      |
//| markets (VIX < 18) with LOW volume (ratio < 0.5). This is a     |
//| "quiet market" specialist: events in low-participation, calm     |
//| environments produce smaller but highly predictable reversions.  |
//|                                                                  |
//| PARAMETERS:                                                      |
//|   - Timeframe: M15                                               |
//|   - SL: 15 pips, TP: 60 pips                                    |
//|   - Spike threshold: 30 pips                                     |
//|   - Filters: VIX < 18, Volume ratio < 0.5 (quiet markets)       |
//|   - Backtest WR: 59.2% (highest win rate on M15)                 |
//|                                                                  |
//| MULTI-PAIR OPERATION:                                            |
//| This EA trades ALL pairs affected by the triggering event's      |
//| currency. Attach it to ANY M15 chart (e.g. EURUSD M15). When a  |
//| USD event fires, it opens trades on EURUSD, GBPUSD, USDJPY,     |
//| USDCHF, AUDUSD, NZDUSD, USDCAD. When an EUR event fires, it    |
//| trades EURUSD, EURGBP, EURJPY, EURCHF, EURAUD. And so on for    |
//| GBP, JPY, CHF, AUD, NZD, CAD events.                            |
//|                                                                  |
//| HOW TO ADD TO CHART:                                             |
//| 1. Open any M15 chart (EURUSD recommended as anchor)             |
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
input int      InpMagicNumber     = 461005;// Magic number (unique per EA)
input double   InpSLPips          = 15;    // Stop loss in pips
input double   InpTPPips          = 60;    // Take profit in pips
input double   InpSpikeThreshold  = 30;    // Minimum spike in pips to trigger
input double   InpVIXThreshold    = 18;    // Maximum VIX level (calm markets)
input double   InpVolumeThreshold = 0.5;   // Maximum volume ratio (quiet markets)

//--- EA instance
class CAlgo05 : public CNewsTraderBase
{
public:
   bool Setup(int magic, double lots, double notional_eur)
   {
      m_sl_pips           = InpSLPips;
      m_tp_pips           = InpTPPips;
      m_spike_threshold   = InpSpikeThreshold;
      m_lot_size          = lots;
      m_notional_eur      = notional_eur;
      m_timeframe         = PERIOD_M15;

      // VIX filter: only trade in calm markets
      m_use_vix_filter    = true;
      m_vix_below         = true;         // Require VIX BELOW threshold
      m_vix_threshold     = InpVIXThreshold;

      // Volume filter: only trade in quiet conditions (low participation)
      m_use_volume_filter = true;
      m_volume_above      = false;        // Require volume BELOW threshold
      m_volume_threshold  = InpVolumeThreshold;

      return Initialize(magic, "Algo05_FadeM15_VIX_LowVol");
   }
};

CAlgo05 trader;

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
