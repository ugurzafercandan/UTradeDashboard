//+------------------------------------------------------------------+
//| P48_v2.mq5 — v2 Signal P48 with M5 Monitoring                  |
//|                                                                  |
//| Original P48: GBPUSD fade, 208 trades, 47.1% WR, $498 net PnL  |
//| v2 adds: M5 candle confirmation, trailing SL, partial close,    |
//|          reversal detection, emergency exit                      |
//|                                                                  |
//| Optimal SL/TP: SL=12 pips, TP=24 pips (2x SL per board spec)     |
//| Magic: 209048 (v2 series)                                       |
//+------------------------------------------------------------------+
#property copyright "USO-469 v2 Signals"
#property version   "1.00"
#property strict

#include <M5MonitorFramework.mqh>

//--- Input parameters
input double   InpLotSize        = 0.01;   // Lot size (fallback)
input double   InpNotionalEUR    = 1000.0; // Target notional per trade in EUR
input int      InpMagicNumber    = 209048; // Magic number (v2 P48)
input double   InpSLPips         = 12;     // Stop loss in pips (optimized from 80th pct MAE)
input double   InpTPPips         = 24;     // Take profit in pips (2x SL per board spec)
input double   InpSpikeThreshold = 10;     // Minimum spike in pips to trigger
input double   InpSpreadMaxMult  = 2.0;    // Max spread multiple vs typical
input int      InpM5ConfirmBars  = 6;      // M5 bars to wait for confirmation (max 30 min)
input int      InpReversalCandles= 3;      // Consecutive M5 candles for reversal exit
input double   InpMAEBreachMult  = 1.5;    // Emergency exit: loss > ATR * this

class CP48v2 : public CM5MonitorBase
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

      // Fade strategy
      m_use_bb_breakout      = false;

      // M5 monitoring parameters
      m_spread_multiple_max  = InpSpreadMaxMult;
      m_m5_confirm_bars      = InpM5ConfirmBars;
      m_reversal_candle_count= InpReversalCandles;
      m_mae_breach_multiple  = InpMAEBreachMult;

      return InitializeV2(magic, "P48_v2", "GBPUSD");
   }

   void ConfigureTimeFilter()
   {
      int blocked[] = {1, 3, 18};
      SetBlockedHours(blocked, 3);
   }
};

CP48v2 trader;

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
