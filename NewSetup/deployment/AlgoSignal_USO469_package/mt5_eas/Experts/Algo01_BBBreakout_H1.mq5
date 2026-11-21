//+------------------------------------------------------------------+
//| Algo01_BBBreakout_H1.mq5                                        |
//| Portfolio Algo #1 — Bollinger Band Breakout on H1                |
//|                                                                  |
//| STRATEGY: Trades in the direction of a Bollinger Band breakout   |
//| after a high/medium-impact economic event. Only triggers during  |
//| high-VIX (fear) regimes with elevated volume.                    |
//|                                                                  |
//| PARAMETERS:                                                      |
//|   - Timeframe: H1                                                |
//|   - SL: 60 pips, TP: 20 pips (inverted R:R, high win-rate)      |
//|   - Filters: VIX > 22, Volume ratio > 2.0, BB std 2.0           |
//|   - Backtest Sharpe: 15.09 (highest in portfolio)                |
//|                                                                  |
//| MULTI-PAIR OPERATION:                                            |
//| This EA trades ALL pairs affected by the triggering event's      |
//| currency. Attach it to ANY H1 chart (e.g. EURUSD H1). When a    |
//| USD event fires, it opens trades on EURUSD, GBPUSD, USDJPY,     |
//| USDCHF, AUDUSD, NZDUSD, USDCAD. When an EUR event fires, it    |
//| trades EURUSD, EURGBP, EURJPY, EURCHF, EURAUD. And so on for    |
//| GBP, JPY, CHF, AUD, NZD, CAD events.                            |
//|                                                                  |
//| HOW TO ADD TO CHART:                                             |
//| 1. Open any H1 chart (EURUSD recommended as anchor)              |
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
input int      InpMagicNumber    = 461001; // Magic number (unique per EA)
input double   InpSLPips         = 60;     // Stop loss in pips
input double   InpTPPips         = 20;     // Take profit in pips
input double   InpVIXThreshold   = 22;     // Minimum VIX level
input double   InpVolumeThreshold= 2.0;    // Minimum volume ratio
input double   InpBBStd          = 2.0;    // Bollinger Band std deviation

//--- EA instance
class CAlgo01 : public CNewsTraderBase
{
public:
   bool Setup(int magic, double lots, double notional_eur)
   {
      m_sl_pips           = InpSLPips;
      m_tp_pips           = InpTPPips;
      m_spike_threshold   = 0;            // BB breakout, not spike-based
      m_lot_size          = lots;
      m_notional_eur      = notional_eur;
      m_timeframe         = PERIOD_H1;

      // Bollinger Band breakout mode (trade WITH the move, not fade)
      m_use_bb_breakout   = true;
      m_bb_std            = InpBBStd;

      // VIX filter: only trade in high-fear regimes
      m_use_vix_filter    = true;
      m_vix_below         = false;        // Require VIX ABOVE threshold
      m_vix_threshold     = InpVIXThreshold;

      // Volume filter: only trade on volume spikes
      m_use_volume_filter = true;
      m_volume_above      = true;
      m_volume_threshold  = InpVolumeThreshold;

      return Initialize(magic, "Algo01_BBBreakout_H1");
   }
};

CAlgo01 trader;

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
