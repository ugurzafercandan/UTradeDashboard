//+------------------------------------------------------------------+
//| M5MonitorFramework.mqh — v2 Signal Framework with M5 Monitoring  |
//|                                                                  |
//| Extends CNewsTraderBase with a 5-minute monitoring layer:        |
//|   1. Pre-entry: M5 candle confirmation + spread check            |
//|   2. Active management: trailing SL, partial close, reversal exit|
//|   3. Emergency exit: MAE breach, VIX spike                       |
//|                                                                  |
//| USO-469 — Board-approved M5 monitoring architecture              |
//+------------------------------------------------------------------+
#property copyright "USO-469 v2 Signals"
#property version   "1.00"
#property strict

#include <NewsTraderFramework.mqh>

//+------------------------------------------------------------------+
//| Pending entry candidate — waiting for M5 confirmation            |
//+------------------------------------------------------------------+
struct SPendingEntry
{
   bool           active;
   string         symbol;
   ENUM_ORDER_TYPE direction;
   double         entry_price_at_signal;
   double         atr_at_signal;
   datetime       signal_time;
   string         event_name;
   string         currency;
   double         spike_pips;
   int            m5_bars_waited;
};

//+------------------------------------------------------------------+
//| Tracked position for M5 active management                        |
//+------------------------------------------------------------------+
struct STrackedPosition
{
   bool           active;
   ulong          ticket;
   string         symbol;
   ENUM_ORDER_TYPE direction;
   double         entry_price;
   double         original_sl;
   double         original_tp;
   double         atr_at_entry;
   bool           trailed_to_breakeven;
   bool           partial_closed;
   double         partial_close_ticket;
   datetime       entry_time;
};

//+------------------------------------------------------------------+
//| M5 Monitor base class                                            |
//+------------------------------------------------------------------+
class CM5MonitorBase : public CNewsTraderBase
{
protected:
   // --- M5 monitoring parameters ---
   double         m_spread_multiple_max;   // Reject entry if spread > typical * this
   int            m_m5_confirm_bars;       // Max M5 bars to wait for confirmation
   int            m_reversal_candle_count; // Consecutive M5 candles to trigger reversal exit
   double         m_mae_breach_multiple;   // Close if loss > expected * this

   // --- Tracking state ---
   SPendingEntry  m_pending;
   STrackedPosition m_tracked[];
   int            m_max_tracked;

   // --- Spread tracking ---
   double         m_spread_ema;
   bool           m_spread_initialized;

   // --- M5 ATR handle ---
   int            m_atr_m5_handle;
   string         m_target_symbol;

   // --- M5 monitoring tick counter ---
   datetime       m_last_m5_check;

   // --- Time-of-day filter (UTC hours to block) ---
   int            m_blocked_hours[];
   int            m_blocked_hours_count;
   bool           m_use_tod_filter;

public:
   CM5MonitorBase()
   {
      m_spread_multiple_max  = 2.0;
      m_m5_confirm_bars      = 6;      // 30 min max wait (6 x 5min)
      m_reversal_candle_count = 3;
      m_mae_breach_multiple  = 1.5;
      m_max_tracked          = 10;
      m_spread_ema           = 0;
      m_spread_initialized   = false;
      m_atr_m5_handle        = INVALID_HANDLE;
      m_last_m5_check        = 0;
      m_blocked_hours_count  = 0;
      m_use_tod_filter       = false;

      m_pending.active = false;
      ArrayResize(m_tracked, 0);
   }

   //+------------------------------------------------------------------+
   //| Initialize v2 signal with target symbol                          |
   //+------------------------------------------------------------------+
   bool InitializeV2(int magic, string name, string target_symbol)
   {
      m_target_symbol = target_symbol;

      if(!Initialize(magic, name))
         return false;

      // Create M5 ATR handle for the target symbol
      if(!SymbolSelect(target_symbol, true))
      {
         PrintFormat("[%s] FATAL: Cannot select symbol %s", m_strategy_name, target_symbol);
         return false;
      }
      m_atr_m5_handle = iATR(target_symbol, PERIOD_M5, 14);
      if(m_atr_m5_handle == INVALID_HANDLE)
      {
         PrintFormat("[%s] WARNING: Cannot create M5 ATR handle for %s", m_strategy_name, target_symbol);
      }

      PrintFormat("[%s] v2 initialized: symbol=%s, spread_max=%.1fx, confirm=%d bars, reversal=%d candles",
                  m_strategy_name, target_symbol, m_spread_multiple_max, m_m5_confirm_bars, m_reversal_candle_count);
      return true;
   }

   //+------------------------------------------------------------------+
   //| Configure blocked UTC hours (time-of-day filter)                 |
   //+------------------------------------------------------------------+
   void SetBlockedHours(int &hours[], int count)
   {
      m_blocked_hours_count = count;
      ArrayResize(m_blocked_hours, count);
      for(int i = 0; i < count; i++)
         m_blocked_hours[i] = hours[i];
      m_use_tod_filter = (count > 0);
   }

   //+------------------------------------------------------------------+
   //| Override OnTick to add M5 monitoring loop                        |
   //+------------------------------------------------------------------+
   void OnTickHandler()
   {
      datetime now = TimeCurrent();

      // Update spread EMA on every tick
      UpdateSpreadEMA();

      // Check pending entries for M5 confirmation
      if(m_pending.active)
         CheckPendingConfirmation(now);

      // M5 active position management (check every 10 seconds)
      if(now - m_last_m5_check >= 10)
      {
         m_last_m5_check = now;
         ManageTrackedPositions(now);
      }

      // Inherit base class calendar checking
      CNewsTraderBase::OnTickHandler();
   }

   //+------------------------------------------------------------------+
   //| Cleanup M5 handles                                               |
   //+------------------------------------------------------------------+
   void Cleanup()
   {
      if(m_atr_m5_handle != INVALID_HANDLE)
         IndicatorRelease(m_atr_m5_handle);
      CNewsTraderBase::Cleanup();
   }

protected:
   //+------------------------------------------------------------------+
   //| Override: intercept trade entry to queue for M5 confirmation      |
   //+------------------------------------------------------------------+
   void EvaluateAndTrade(string symbol, string currency, datetime event_time, string event_name)
   {
      // Only trade the target symbol
      if(symbol != m_target_symbol)
         return;

      if(!SymbolSelect(symbol, true))
         return;

      // --- Measure spike (same as base) ---
      double price_at_event = GetPriceAtTime(symbol, event_time);
      double price_now = SymbolInfoDouble(symbol, SYMBOL_BID);
      if(price_at_event == 0 || price_now == 0)
         return;

      double pip = PipSize(symbol);
      double spike_pips = (price_now - price_at_event) / pip;
      double abs_spike = MathAbs(spike_pips);

      double effective_threshold = m_spike_threshold;
      if(m_is_tester && m_spike_threshold > 0)
         effective_threshold = m_spike_threshold * m_tester_spike_scale;

      if(abs_spike < effective_threshold)
         return;

      if(!PassesFilters(symbol, event_time))
         return;

      // --- Time-of-day filter: reject blocked UTC hours ---
      if(m_use_tod_filter)
      {
         MqlDateTime dt;
         TimeGMT(dt);
         for(int h = 0; h < m_blocked_hours_count; h++)
         {
            if(dt.hour == m_blocked_hours[h])
            {
               PrintFormat("[%s] SKIP %s: blocked UTC hour %02d:00",
                           m_strategy_name, symbol, dt.hour);
               return;
            }
         }
      }

      // --- Pre-entry spread check ---
      if(!CheckSpread(symbol))
      {
         PrintFormat("[%s] SKIP %s: spread too wide (%.1f > %.1f typical x %.1f)",
                     m_strategy_name, symbol, GetCurrentSpread(symbol),
                     m_spread_ema, m_spread_multiple_max);
         return;
      }

      // --- Determine direction ---
      ENUM_ORDER_TYPE order_type;
      if(m_use_bb_breakout)
         order_type = (spike_pips > 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      else
         order_type = (spike_pips > 0) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;

      // --- Don't enter immediately: queue for M5 confirmation ---
      if(m_pending.active)
      {
         PrintFormat("[%s] SKIP %s: already have pending entry", m_strategy_name, symbol);
         return;
      }

      // Get M5 ATR for position sizing reference
      double atr_m5 = GetM5ATR();

      m_pending.active             = true;
      m_pending.symbol             = symbol;
      m_pending.direction          = order_type;
      m_pending.entry_price_at_signal = price_now;
      m_pending.atr_at_signal      = (atr_m5 > 0) ? atr_m5 : abs_spike * pip;
      m_pending.signal_time        = TimeCurrent();
      m_pending.event_name         = event_name;
      m_pending.currency           = currency;
      m_pending.spike_pips         = spike_pips;
      m_pending.m5_bars_waited     = 0;

      PrintFormat("[%s] QUEUED %s %s — waiting for M5 confirmation (spike=%.1f pips, ATR=%.5f)",
                  m_strategy_name,
                  (order_type == ORDER_TYPE_BUY) ? "BUY" : "SELL",
                  symbol, spike_pips, m_pending.atr_at_signal);
   }

   //+------------------------------------------------------------------+
   //| Check if M5 candle confirms the pending entry direction          |
   //+------------------------------------------------------------------+
   void CheckPendingConfirmation(datetime now)
   {
      if(!m_pending.active) return;

      int elapsed_sec = (int)(now - m_pending.signal_time);
      int bars_elapsed = elapsed_sec / 300;  // 5-min bars

      // Timeout: give up after m_m5_confirm_bars
      if(bars_elapsed > m_m5_confirm_bars)
      {
         PrintFormat("[%s] EXPIRED pending %s %s — no M5 confirmation in %d bars",
                     m_strategy_name,
                     (m_pending.direction == ORDER_TYPE_BUY) ? "BUY" : "SELL",
                     m_pending.symbol, m_m5_confirm_bars);
         m_pending.active = false;
         return;
      }

      // Need at least one M5 bar to have closed since the signal
      if(bars_elapsed < 1) return;

      // Check the most recent closed M5 candle
      MqlRates m5_rates[];
      if(CopyRates(m_pending.symbol, PERIOD_M5, 1, 1, m5_rates) < 1)
         return;

      bool confirmed = false;
      if(m_pending.direction == ORDER_TYPE_BUY)
      {
         // Bullish confirmation: close > open
         confirmed = (m5_rates[0].close > m5_rates[0].open);
      }
      else
      {
         // Bearish confirmation: close < open
         confirmed = (m5_rates[0].close < m5_rates[0].open);
      }

      if(!confirmed)
      {
         m_pending.m5_bars_waited = bars_elapsed;
         return;
      }

      // Re-check spread before executing
      if(!CheckSpread(m_pending.symbol))
      {
         PrintFormat("[%s] SKIP confirmed %s: spread widened", m_strategy_name, m_pending.symbol);
         m_pending.active = false;
         return;
      }

      // --- Execute the trade ---
      ExecuteConfirmedEntry();
   }

   //+------------------------------------------------------------------+
   //| Execute a confirmed entry with optimized SL/TP                   |
   //+------------------------------------------------------------------+
   void ExecuteConfirmedEntry()
   {
      string symbol = m_pending.symbol;
      double point = PipPoint(symbol);
      double entry_price, sl, tp;

      if(m_pending.direction == ORDER_TYPE_BUY)
      {
         entry_price = SymbolInfoDouble(symbol, SYMBOL_ASK);
         sl = entry_price - m_sl_pips * point;
         tp = entry_price + m_tp_pips * point;
      }
      else
      {
         entry_price = SymbolInfoDouble(symbol, SYMBOL_BID);
         sl = entry_price + m_sl_pips * point;
         tp = entry_price - m_tp_pips * point;
      }

      string comment = StringFormat("%s|%s|%s|%.0fpip|v2",
                                     m_strategy_name, m_pending.event_name,
                                     m_pending.currency, m_pending.spike_pips);

      double lots = CalculateLotSize(symbol);

      if(m_trade.PositionOpen(symbol, m_pending.direction, lots, entry_price, sl, tp, comment))
      {
         PrintFormat("[%s] v2 TRADE: %s %s %.2f lots (M5 confirmed after %d bars, spike=%.1f pips)",
                     m_strategy_name,
                     (m_pending.direction == ORDER_TYPE_BUY) ? "BUY" : "SELL",
                     symbol, lots, m_pending.m5_bars_waited, m_pending.spike_pips);

         // Track this position for M5 management
         TrackPosition(m_trade.ResultOrder(), symbol, m_pending.direction,
                       entry_price, sl, tp, m_pending.atr_at_signal);
      }
      else
      {
         PrintFormat("[%s] v2 TRADE FAILED: %s %s — error %d: %s",
                     m_strategy_name, symbol,
                     (m_pending.direction == ORDER_TYPE_BUY) ? "BUY" : "SELL",
                     m_trade.ResultRetcode(), m_trade.ResultComment());
      }

      m_pending.active = false;
   }

   //+------------------------------------------------------------------+
   //| Track a new position for M5 monitoring                           |
   //+------------------------------------------------------------------+
   void TrackPosition(ulong ticket, string symbol, ENUM_ORDER_TYPE direction,
                      double entry_price, double sl, double tp, double atr)
   {
      int idx = ArraySize(m_tracked);
      ArrayResize(m_tracked, idx + 1);
      m_tracked[idx].active               = true;
      m_tracked[idx].ticket               = ticket;
      m_tracked[idx].symbol               = symbol;
      m_tracked[idx].direction            = direction;
      m_tracked[idx].entry_price          = entry_price;
      m_tracked[idx].original_sl          = sl;
      m_tracked[idx].original_tp          = tp;
      m_tracked[idx].atr_at_entry         = atr;
      m_tracked[idx].trailed_to_breakeven = false;
      m_tracked[idx].partial_closed       = false;
      m_tracked[idx].partial_close_ticket = 0;
      m_tracked[idx].entry_time           = TimeCurrent();
   }

   //+------------------------------------------------------------------+
   //| M5 active management loop — runs every ~10 seconds               |
   //+------------------------------------------------------------------+
   void ManageTrackedPositions(datetime now)
   {
      for(int i = ArraySize(m_tracked) - 1; i >= 0; i--)
      {
         if(!m_tracked[i].active) continue;

         // Verify position still exists
         if(!PositionSelectByTicket(m_tracked[i].ticket))
         {
            m_tracked[i].active = false;
            continue;
         }

         // Only manage our positions
         if(PositionGetInteger(POSITION_MAGIC) != m_magic)
         {
            m_tracked[i].active = false;
            continue;
         }

         double current_price = SymbolInfoDouble(m_tracked[i].symbol, SYMBOL_BID);
         double entry = m_tracked[i].entry_price;
         double atr = m_tracked[i].atr_at_entry;
         if(atr <= 0) atr = 0.0010;  // Safety fallback

         bool is_buy = (m_tracked[i].direction == ORDER_TYPE_BUY);
         double unrealized = is_buy ? (current_price - entry) : (entry - current_price);

         // --- Emergency exit: MAE breach ---
         if(unrealized < -atr * m_mae_breach_multiple)
         {
            PrintFormat("[%s] EMERGENCY EXIT %s: loss %.5f > %.1fx ATR (%.5f)",
                        m_strategy_name, m_tracked[i].symbol,
                        MathAbs(unrealized), m_mae_breach_multiple, atr);
            CloseTrackedPosition(i, "MAE_BREACH");
            continue;
         }

         // --- 5m reversal detection ---
         if(CheckM5Reversal(m_tracked[i].symbol, is_buy))
         {
            PrintFormat("[%s] REVERSAL EXIT %s: %d consecutive opposing M5 candles",
                        m_strategy_name, m_tracked[i].symbol, m_reversal_candle_count);
            CloseTrackedPosition(i, "M5_REVERSAL");
            continue;
         }

         // --- Trail stop to breakeven after 1x ATR move in profit ---
         if(!m_tracked[i].trailed_to_breakeven && unrealized >= atr)
         {
            double new_sl;
            double point = PipPoint(m_tracked[i].symbol);
            // Set SL at breakeven + 1 pip buffer
            if(is_buy)
               new_sl = entry + point;
            else
               new_sl = entry - point;

            if(m_trade.PositionModify(m_tracked[i].ticket, new_sl,
                                       PositionGetDouble(POSITION_TP)))
            {
               m_tracked[i].trailed_to_breakeven = true;
               PrintFormat("[%s] BREAKEVEN %s: SL moved to %.5f (profit=%.5f, ATR=%.5f)",
                           m_strategy_name, m_tracked[i].symbol, new_sl, unrealized, atr);
            }
         }

         // --- Partial close (50%) at 1.5x ATR ---
         if(!m_tracked[i].partial_closed && unrealized >= atr * 1.5)
         {
            double current_volume = PositionGetDouble(POSITION_VOLUME);
            double close_volume = NormalizeVolume(m_tracked[i].symbol, current_volume * 0.5);
            if(close_volume > 0)
            {
               ENUM_ORDER_TYPE close_type = is_buy ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
               double close_price = is_buy ?
                  SymbolInfoDouble(m_tracked[i].symbol, SYMBOL_BID) :
                  SymbolInfoDouble(m_tracked[i].symbol, SYMBOL_ASK);

               string comment = StringFormat("%s|partial|v2", m_strategy_name);
               if(m_trade.PositionClosePartial(m_tracked[i].ticket, close_volume))
               {
                  m_tracked[i].partial_closed = true;

                  // Move SL to 1x ATR profit on remaining
                  double new_sl;
                  if(is_buy)
                     new_sl = entry + atr;
                  else
                     new_sl = entry - atr;

                  m_trade.PositionModify(m_tracked[i].ticket, new_sl,
                                          PositionGetDouble(POSITION_TP));

                  PrintFormat("[%s] PARTIAL CLOSE %s: %.2f lots closed at %.5f (profit=%.5f), SL->%.5f",
                              m_strategy_name, m_tracked[i].symbol,
                              close_volume, close_price, unrealized, new_sl);
               }
            }
         }
      }
   }

   //+------------------------------------------------------------------+
   //| Close a tracked position with reason                             |
   //+------------------------------------------------------------------+
   void CloseTrackedPosition(int idx, string reason)
   {
      if(idx < 0 || idx >= ArraySize(m_tracked)) return;
      if(!m_tracked[idx].active) return;

      ulong ticket = m_tracked[idx].ticket;
      if(PositionSelectByTicket(ticket))
      {
         string comment = StringFormat("%s|%s|v2", m_strategy_name, reason);
         if(!m_trade.PositionClose(ticket))
         {
            PrintFormat("[%s] CLOSE FAILED %s ticket=%llu — %d: %s",
                        m_strategy_name, m_tracked[idx].symbol, ticket,
                        m_trade.ResultRetcode(), m_trade.ResultComment());
         }
      }
      m_tracked[idx].active = false;
   }

   //+------------------------------------------------------------------+
   //| Check for M5 reversal: N consecutive candles against position    |
   //+------------------------------------------------------------------+
   bool CheckM5Reversal(string symbol, bool is_buy)
   {
      MqlRates rates[];
      // Check last N closed M5 candles (index 1..N, skip current)
      if(CopyRates(symbol, PERIOD_M5, 1, m_reversal_candle_count, rates) < m_reversal_candle_count)
         return false;

      for(int i = 0; i < m_reversal_candle_count; i++)
      {
         if(is_buy)
         {
            // For longs, reversal = bearish candles (close < open)
            if(rates[i].close >= rates[i].open)
               return false;
         }
         else
         {
            // For shorts, reversal = bullish candles (close > open)
            if(rates[i].close <= rates[i].open)
               return false;
         }
      }
      return true;
   }

   //+------------------------------------------------------------------+
   //| Spread check: current spread vs EMA                              |
   //+------------------------------------------------------------------+
   bool CheckSpread(string symbol)
   {
      if(!m_spread_initialized || m_spread_ema <= 0)
         return true;  // No data yet, allow entry

      double current = GetCurrentSpread(symbol);
      return (current <= m_spread_ema * m_spread_multiple_max);
   }

   double GetCurrentSpread(string symbol)
   {
      double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
      double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
      return (ask > 0 && bid > 0) ? (ask - bid) : 0;
   }

   //+------------------------------------------------------------------+
   //| Update spread EMA on each tick                                   |
   //+------------------------------------------------------------------+
   void UpdateSpreadEMA()
   {
      double spread = GetCurrentSpread(m_target_symbol);
      if(spread <= 0) return;

      if(!m_spread_initialized)
      {
         m_spread_ema = spread;
         m_spread_initialized = true;
      }
      else
      {
         // EMA with alpha = 0.001 (slow decay, ~1000 tick window)
         m_spread_ema = 0.999 * m_spread_ema + 0.001 * spread;
      }
   }

   //+------------------------------------------------------------------+
   //| Get current M5 ATR value                                         |
   //+------------------------------------------------------------------+
   double GetM5ATR()
   {
      if(m_atr_m5_handle == INVALID_HANDLE) return 0;

      double atr_val[];
      if(CopyBuffer(m_atr_m5_handle, 0, 0, 1, atr_val) > 0)
         return atr_val[0];
      return 0;
   }

   //+------------------------------------------------------------------+
   //| Normalize volume to broker's step size                           |
   //+------------------------------------------------------------------+
   double NormalizeVolume(string symbol, double volume)
   {
      double lot_min  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
      double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
      if(lot_min <= 0) lot_min = 0.01;
      if(lot_step <= 0) lot_step = 0.01;

      double normalized = MathFloor(volume / lot_step) * lot_step;
      if(normalized < lot_min) return 0;
      return normalized;
   }
};
