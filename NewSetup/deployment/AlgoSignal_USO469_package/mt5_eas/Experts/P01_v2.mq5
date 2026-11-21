//+------------------------------------------------------------------+
//| P01_v2.mq5 — v2 Signal P1 with M5 Monitoring                   |
//|                                                                  |
//| Original P1: EURUSD fade, 247 trades, 46.2% WR, $545 net PnL   |
//| v2 adds: M5 candle confirmation, trailing SL, partial close,    |
//|          reversal detection, emergency exit                      |
//|                                                                  |
//| Optimal SL/TP: SL=14 pips, TP=28 pips (2x SL per board spec)     |
//| Magic: 209001 (v2 series)                                       |
//+------------------------------------------------------------------+
#property copyright "USO-469 v2 Signals"
#property version   "1.00"
#property strict

#include <M5MonitorFramework.mqh>

//--- Input parameters
input double   InpLotSize        = 0.01;   // Lot size (fallback)
input double   InpNotionalEUR    = 1000.0; // Target notional per trade in EUR
input int      InpMagicNumber    = 209001; // Magic number (v2 P1)
input double   InpSLPips         = 14;     // Stop loss in pips (optimized from 80th pct MAE)
input double   InpTPPips         = 28;     // Take profit in pips (2x SL per board spec)
input double   InpSpikeThreshold = 10;     // Minimum spike in pips to trigger
input double   InpSpreadMaxMult  = 2.0;    // Max spread multiple vs typical
input int      InpM5ConfirmBars  = 6;      // M5 bars to wait for confirmation (max 30 min)
input int      InpReversalCandles= 3;      // Consecutive M5 candles for reversal exit
input double   InpMAEBreachMult  = 1.5;    // Emergency exit: loss > ATR * this

class CP01v2 : public CM5MonitorBase
{
public:
   bool Setup(int magic, double lots, double notional_eur)
   {
      m_sl_pips              = InpSLPips;
      m_tp_pips              = InpTPPips;
      m_spike_threshold      = InpSpikeThreshold;
      m_lot_size             = lots;
      m_notional_eur         = notional_eur;
      m_timeframe            = PERIOD_M5;

      // Fade strategy: trade against the spike
      m_use_bb_breakout      = false;

      // M5 monitoring parameters
      m_spread_multiple_max  = InpSpreadMaxMult;
      m_m5_confirm_bars      = InpM5ConfirmBars;
      m_reversal_candle_count= InpReversalCandles;
      m_mae_breach_multiple  = InpMAEBreachMult;

      return InitializeV2(magic, "P01_v2", "EURUSD");
   }

   void ConfigureTimeFilter()
   {
      int blocked[] = {1, 3, 18};
      SetBlockedHours(blocked, 3);
   }
};

CP01v2 trader;

//+------------------------------------------------------------------+
int OnInit()
{
   if(!trader.Setup(InpMagicNumber, InpLotSize, InpNotionalEUR))
      return INIT_FAILED;
   trader.ConfigureTimeFilter();
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
