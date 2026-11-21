//+------------------------------------------------------------------+
//| NewsTraderFramework.mqh — Shared framework for news-event EAs    |
//|                                                                  |
//| HOW THESE EAs TRADE MULTIPLE PAIRS:                              |
//|                                                                  |
//| Each EA is attached to ONE chart but trades ALL pairs affected   |
//| by economic events. When an NFP (USD) event fires, the EA opens  |
//| trades on EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD, and  |
//| USDCAD simultaneously. When an ECB (EUR) event fires, it trades  |
//| EURUSD, EURGBP, EURJPY, EURCHF, EURAUD.                         |
//|                                                                  |
//| Attach the EA to any chart (e.g. EURUSD M5). The chart timeframe |
//| must match the EA's intended timeframe (M5, M15, or H1). The EA  |
//| uses iClose/iRSI/etc on remote symbols to read other pairs' data.|
//|                                                                  |
//| Each EA uses a unique MagicNumber so multiple EAs can run on the |
//| same account without interfering with each other's positions.    |
//+------------------------------------------------------------------+
#property copyright "USO-461/462 Portfolio"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
//| Currency-to-pairs mapping (mirrors forex_mapping.py)             |
//+------------------------------------------------------------------+
// Each economic event affects a specific currency. This mapping defines
// which forex pairs to trade when that currency's event fires.
// For example, a USD event triggers trades on 7 pairs where USD is
// either the base or quote currency.

struct CurrencyPairMapping
{
   string currency;
   string pairs[];
};

struct CSVCalendarEvent
{
   datetime event_time;
   string   currency;
   string   event_name;
   string   impact;
};

class CNewsTraderBase
{
protected:
   // --- Trade management ---
   CTrade         m_trade;
   int            m_magic;
   double         m_lot_size;       // Fallback fixed lot size
   double         m_notional_eur;   // Target notional per trade in EUR (0 = use fixed lot)
   int            m_slippage;

   // --- Strategy parameters ---
   double         m_sl_pips;
   double         m_tp_pips;
   double         m_spike_threshold;   // min 15m move in pips to trigger entry
   string         m_strategy_name;
   ENUM_TIMEFRAMES m_timeframe;

   // --- Filters (set by subclass) ---
   bool           m_use_vix_filter;
   double         m_vix_threshold;
   bool           m_vix_below;          // true = require VIX < threshold
   bool           m_use_volume_filter;
   double         m_volume_threshold;
   bool           m_volume_above;       // true = require vol ratio > threshold
   bool           m_use_gold_filter;
   bool           m_gold_negative_corr; // true = require negative gold correlation
   bool           m_use_vol_regime;
   string         m_vol_regime_target;  // "high_only", "low_only", etc.
   bool           m_use_mean_rev_gate;
   bool           m_use_bb_breakout;
   double         m_bb_std;

   // --- Calendar tracking ---
   datetime       m_last_event_check;
   int            m_check_interval_sec;

   // --- Currency pair map ---
   CurrencyPairMapping m_pair_map[];

   // --- CSV calendar for Strategy Tester ---
   bool              m_is_tester;
   CSVCalendarEvent  m_csv_events[];
   int               m_csv_scan_idx;
   bool              m_csv_traded[];      // Track which CSV events have been traded

   // --- Tester spike scaling ---
   double         m_tester_spike_scale;   // Scale factor for spike thresholds in tester

   // --- Indicator handles (per symbol cache) ---
   struct SymbolIndicators
   {
      string symbol;
      int    rsi_handle;
      int    macd_handle;
      int    bb_handle;
      int    atr_handle;
   };
   SymbolIndicators m_indicators[];

public:
   CNewsTraderBase()
   {
      m_magic = 0;
      m_lot_size = 0.01;
      m_notional_eur = 1000.0;
      m_slippage = 20;
      m_sl_pips = 15;
      m_tp_pips = 100;
      m_spike_threshold = 20;
      m_strategy_name = "NewsTrader";
      m_timeframe = PERIOD_M5;
      m_use_vix_filter = false;
      m_vix_threshold = 20;
      m_vix_below = true;
      m_use_volume_filter = false;
      m_volume_threshold = 1.5;
      m_volume_above = true;
      m_use_gold_filter = false;
      m_gold_negative_corr = false;
      m_use_vol_regime = false;
      m_vol_regime_target = "high_only";
      m_use_mean_rev_gate = false;
      m_use_bb_breakout = false;
      m_bb_std = 2.0;
      m_last_event_check = 0;
      m_check_interval_sec = 10;
      m_is_tester = false;
      m_csv_scan_idx = 0;
      m_tester_spike_scale = 0.5;

      InitPairMap();
   }

   //+------------------------------------------------------------------+
   //| Initialize: call from OnInit()                                    |
   //+------------------------------------------------------------------+
   bool Initialize(int magic, string name)
   {
      m_magic = magic;
      m_strategy_name = name;
      m_trade.SetExpertMagicNumber(magic);
      m_trade.SetDeviationInPoints(m_slippage);
      m_trade.SetTypeFilling(ORDER_FILLING_IOC);

      m_is_tester = (bool)MQLInfoInteger(MQL_TESTER);

      if(m_is_tester)
      {
         m_check_interval_sec = 5;  // Check more frequently in tester
         if(!LoadCSVCalendar("forex_factory_events.csv"))
         {
            PrintFormat("[%s] FATAL: Cannot load forex_factory_events.csv — place it in MQL5\\Files\\",
                        m_strategy_name);
            return false;
         }
         PrintFormat("[%s] Tester mode: loaded %d events from CSV", m_strategy_name, ArraySize(m_csv_events));
         PrintFormat("[%s] Tester mode: chart=%s — trading events for currencies in this pair only", m_strategy_name, _Symbol);
         PrintFormat("[%s] Tester mode: cross-symbol filters (VIX, volume, gold) bypassed — data unavailable", m_strategy_name);
         PrintFormat("[%s] Tester mode: spike threshold scaled to %.0f%% (%.0f -> %.0f pips)",
                     m_strategy_name, m_tester_spike_scale * 100,
                     m_spike_threshold, m_spike_threshold * m_tester_spike_scale);
         PrintFormat("[%s] Tester mode: event window 2-15min, one trade per event",
                     m_strategy_name);
      }

      // Pre-load indicator handles for all mapped pairs
      for(int i = 0; i < ArraySize(m_pair_map); i++)
      {
         for(int j = 0; j < ArraySize(m_pair_map[i].pairs); j++)
         {
            string sym = m_pair_map[i].pairs[j];
            if(!SymbolSelect(sym, true))
            {
               PrintFormat("[%s] Warning: symbol %s not available on this broker", m_strategy_name, sym);
               continue;
            }
            CreateIndicatorHandles(sym);
         }
      }

      PrintFormat("[%s] Initialized: magic=%d, SL=%.0f, TP=%.0f, spike>%.0f pips, notional=%.0f EUR",
                  m_strategy_name, m_magic, m_sl_pips, m_tp_pips, m_spike_threshold, m_notional_eur);
      return true;
   }

   //+------------------------------------------------------------------+
   //| OnTick handler: call from EA's OnTick()                          |
   //+------------------------------------------------------------------+
   void OnTickHandler()
   {
      datetime now = TimeCurrent();
      if(now - m_last_event_check < m_check_interval_sec)
         return;
      m_last_event_check = now;

      CheckCalendarEvents(now);
   }

   //+------------------------------------------------------------------+
   //| Cleanup: call from OnDeinit()                                    |
   //+------------------------------------------------------------------+
   void Cleanup()
   {
      for(int i = 0; i < ArraySize(m_indicators); i++)
      {
         if(m_indicators[i].rsi_handle != INVALID_HANDLE)  IndicatorRelease(m_indicators[i].rsi_handle);
         if(m_indicators[i].macd_handle != INVALID_HANDLE) IndicatorRelease(m_indicators[i].macd_handle);
         if(m_indicators[i].bb_handle != INVALID_HANDLE)   IndicatorRelease(m_indicators[i].bb_handle);
         if(m_indicators[i].atr_handle != INVALID_HANDLE)  IndicatorRelease(m_indicators[i].atr_handle);
      }
   }

protected:
   //+------------------------------------------------------------------+
   //| Build the currency → pairs mapping                               |
   //+------------------------------------------------------------------+
   void InitPairMap()
   {
      ArrayResize(m_pair_map, 8);

      m_pair_map[0].currency = "USD";
      ArrayResize(m_pair_map[0].pairs, 7);
      m_pair_map[0].pairs[0]="EURUSD"; m_pair_map[0].pairs[1]="GBPUSD";
      m_pair_map[0].pairs[2]="USDJPY"; m_pair_map[0].pairs[3]="USDCHF";
      m_pair_map[0].pairs[4]="AUDUSD"; m_pair_map[0].pairs[5]="NZDUSD";
      m_pair_map[0].pairs[6]="USDCAD";

      m_pair_map[1].currency = "EUR";
      ArrayResize(m_pair_map[1].pairs, 5);
      m_pair_map[1].pairs[0]="EURUSD"; m_pair_map[1].pairs[1]="EURGBP";
      m_pair_map[1].pairs[2]="EURJPY"; m_pair_map[1].pairs[3]="EURCHF";
      m_pair_map[1].pairs[4]="EURAUD";

      m_pair_map[2].currency = "GBP";
      ArrayResize(m_pair_map[2].pairs, 4);
      m_pair_map[2].pairs[0]="GBPUSD"; m_pair_map[2].pairs[1]="EURGBP";
      m_pair_map[2].pairs[2]="GBPJPY"; m_pair_map[2].pairs[3]="GBPCHF";

      m_pair_map[3].currency = "JPY";
      ArrayResize(m_pair_map[3].pairs, 4);
      m_pair_map[3].pairs[0]="USDJPY"; m_pair_map[3].pairs[1]="EURJPY";
      m_pair_map[3].pairs[2]="GBPJPY"; m_pair_map[3].pairs[3]="AUDJPY";

      m_pair_map[4].currency = "CHF";
      ArrayResize(m_pair_map[4].pairs, 3);
      m_pair_map[4].pairs[0]="USDCHF"; m_pair_map[4].pairs[1]="EURCHF";
      m_pair_map[4].pairs[2]="GBPCHF";

      m_pair_map[5].currency = "AUD";
      ArrayResize(m_pair_map[5].pairs, 3);
      m_pair_map[5].pairs[0]="AUDUSD"; m_pair_map[5].pairs[1]="EURAUD";
      m_pair_map[5].pairs[2]="AUDJPY";

      m_pair_map[6].currency = "NZD";
      ArrayResize(m_pair_map[6].pairs, 1);
      m_pair_map[6].pairs[0]="NZDUSD";

      m_pair_map[7].currency = "CAD";
      ArrayResize(m_pair_map[7].pairs, 1);
      m_pair_map[7].pairs[0]="USDCAD";
   }

   //+------------------------------------------------------------------+
   //| Create indicator handles for a symbol                            |
   //+------------------------------------------------------------------+
   void CreateIndicatorHandles(string symbol)
   {
      // Check if already created
      for(int i = 0; i < ArraySize(m_indicators); i++)
         if(m_indicators[i].symbol == symbol) return;

      int idx = ArraySize(m_indicators);
      ArrayResize(m_indicators, idx + 1);
      m_indicators[idx].symbol = symbol;
      m_indicators[idx].rsi_handle = iRSI(symbol, m_timeframe, 14, PRICE_CLOSE);
      m_indicators[idx].macd_handle = iMACD(symbol, m_timeframe, 12, 26, 9, PRICE_CLOSE);
      m_indicators[idx].bb_handle = iBands(symbol, m_timeframe, 20, 0, m_bb_std, PRICE_CLOSE);
      m_indicators[idx].atr_handle = iATR(symbol, m_timeframe, 14);
   }

   //+------------------------------------------------------------------+
   //| Get indicator handle for a specific symbol                       |
   //+------------------------------------------------------------------+
   int GetRSIHandle(string symbol)   { return GetHandle(symbol, 0); }
   int GetMACDHandle(string symbol)  { return GetHandle(symbol, 1); }
   int GetBBHandle(string symbol)    { return GetHandle(symbol, 2); }
   int GetATRHandle(string symbol)   { return GetHandle(symbol, 3); }

   int GetHandle(string symbol, int type)
   {
      for(int i = 0; i < ArraySize(m_indicators); i++)
      {
         if(m_indicators[i].symbol == symbol)
         {
            switch(type)
            {
               case 0: return m_indicators[i].rsi_handle;
               case 1: return m_indicators[i].macd_handle;
               case 2: return m_indicators[i].bb_handle;
               case 3: return m_indicators[i].atr_handle;
            }
         }
      }
      return INVALID_HANDLE;
   }

   //+------------------------------------------------------------------+
   //| Pip size for a symbol (handles JPY and non-JPY pairs)            |
   //+------------------------------------------------------------------+
   double PipSize(string symbol)
   {
      int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
      if(digits == 3 || digits == 2)
         return 0.01;     // JPY pairs
      return 0.0001;      // Standard pairs
   }

   double PipPoint(string symbol)
   {
      return SymbolInfoDouble(symbol, SYMBOL_POINT) *
             ((SymbolInfoInteger(symbol, SYMBOL_DIGITS) == 5 ||
               SymbolInfoInteger(symbol, SYMBOL_DIGITS) == 3) ? 10 : 1);
   }

   //+------------------------------------------------------------------+
   //| Calculate lot size for equal EUR notional exposure                |
   //| Formula: lots = notional_eur / (contract_size * base_price_eur)  |
   //+------------------------------------------------------------------+
   double CalculateLotSize(string symbol)
   {
      if(m_notional_eur <= 0)
         return m_lot_size;

      double contract_size = SymbolInfoDouble(symbol, SYMBOL_TRADE_CONTRACT_SIZE);
      if(contract_size <= 0)
         return m_lot_size;

      string base_ccy = StringSubstr(symbol, 0, 3);
      double base_to_eur = GetCurrencyRateToEUR(base_ccy);
      if(base_to_eur <= 0)
         return m_lot_size;

      double raw_lots = m_notional_eur / (contract_size * base_to_eur);

      double lot_min  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
      double lot_max  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
      double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
      if(lot_min <= 0) lot_min = 0.01;
      if(lot_max <= 0) lot_max = 100.0;
      if(lot_step <= 0) lot_step = 0.01;

      double lots = MathFloor(raw_lots / lot_step) * lot_step;
      if(lots < lot_min) lots = lot_min;
      if(lots > lot_max) lots = lot_max;

      return lots;
   }

   //+------------------------------------------------------------------+
   //| Get exchange rate: 1 unit of ccy expressed in EUR                 |
   //+------------------------------------------------------------------+
   double GetCurrencyRateToEUR(string ccy)
   {
      if(ccy == "EUR") return 1.0;

      // Try EURccy pair (e.g. EURUSD -> 1 USD = 1/EURUSD EUR)
      string eur_pair = "EUR" + ccy;
      if(SymbolSelect(eur_pair, true))
      {
         double bid = SymbolInfoDouble(eur_pair, SYMBOL_BID);
         if(bid > 0) return 1.0 / bid;
      }

      // Try ccyEUR pair (e.g. GBPEUR -> 1 GBP = GBPEUR EUR)
      string pair_eur = ccy + "EUR";
      if(SymbolSelect(pair_eur, true))
      {
         double bid = SymbolInfoDouble(pair_eur, SYMBOL_BID);
         if(bid > 0) return bid;
      }

      // Cross through USD: ccy->USD->EUR
      double ccy_to_usd = GetCurrencyRateToUSD(ccy);
      double eur_usd = 0;
      if(SymbolSelect("EURUSD", true))
         eur_usd = SymbolInfoDouble("EURUSD", SYMBOL_BID);
      if(ccy_to_usd > 0 && eur_usd > 0)
         return ccy_to_usd / eur_usd;

      // For metals: XAU contract = 1 troy oz, price is in USD
      if(ccy == "XAU" || ccy == "XAG")
      {
         double metal_usd = SymbolInfoDouble(ccy + "USD", SYMBOL_BID);
         if(metal_usd > 0 && eur_usd > 0)
            return metal_usd / eur_usd;
      }

      return 0;
   }

   //+------------------------------------------------------------------+
   //| Get exchange rate: 1 unit of ccy expressed in USD                 |
   //+------------------------------------------------------------------+
   double GetCurrencyRateToUSD(string ccy)
   {
      if(ccy == "USD") return 1.0;

      // xxxUSD pairs (EURUSD, GBPUSD, AUDUSD, NZDUSD)
      string pair1 = ccy + "USD";
      if(SymbolSelect(pair1, true))
      {
         double bid = SymbolInfoDouble(pair1, SYMBOL_BID);
         if(bid > 0) return bid;
      }

      // USDxxx pairs (USDJPY, USDCHF, USDCAD) -> 1 ccy = 1/rate USD
      string pair2 = "USD" + ccy;
      if(SymbolSelect(pair2, true))
      {
         double bid = SymbolInfoDouble(pair2, SYMBOL_BID);
         if(bid > 0) return 1.0 / bid;
      }

      return 0;
   }

   //+------------------------------------------------------------------+
   //| Check MT5 economic calendar for recent events                    |
   //+------------------------------------------------------------------+
   void CheckCalendarEvents(datetime now)
   {
      if(m_is_tester)
      {
         CheckCSVEvents(now);
         return;
      }

      // --- Live mode: use MT5 built-in calendar ---
      // Look at events in the last 20 minutes (spike measurement window)
      datetime from_time = now - 20 * 60;

      MqlCalendarValue values[];
      int count = CalendarValueHistory(values, from_time, now);
      if(count <= 0) return;

      for(int i = 0; i < count; i++)
      {
         // Only process events with actual values (released)
         if(!values[i].HasActualValue()) continue;

         MqlCalendarEvent event_info;
         if(!CalendarEventById(values[i].event_id, event_info)) continue;

         MqlCalendarCountry country_info;
         if(!CalendarCountryById(event_info.country_id, country_info)) continue;

         // Filter: high and medium impact only
         if(event_info.importance != CALENDAR_IMPORTANCE_HIGH &&
            event_info.importance != CALENDAR_IMPORTANCE_MODERATE)
            continue;

         string currency = country_info.currency;
         datetime event_time = values[i].time;

         // Skip if event is too old (already processed) or too recent (no spike yet)
         int age_sec = (int)(now - event_time);
         if(age_sec < 60 || age_sec > 15 * 60) continue;  // Need 1-15 min for spike

         // Skip if we already have a position from this event (check by time window)
         if(HasRecentPosition(currency, event_time)) continue;

         // Get affected pairs and evaluate each
         string pairs[];
         GetAffectedPairs(currency, pairs);

         for(int p = 0; p < ArraySize(pairs); p++)
         {
            EvaluateAndTrade(pairs[p], currency, event_time, event_info.name);
         }
      }
   }

   //+------------------------------------------------------------------+
   //| Load CSV calendar file for Strategy Tester backtesting           |
   //| File format: datetime_utc,currency,event_name,impact,actual,...  |
   //| Datetimes as "YYYY.MM.DD HH:MM"                                 |
   //+------------------------------------------------------------------+
   bool LoadCSVCalendar(string filename)
   {
      int handle = FileOpen(filename, FILE_READ|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
      if(handle == INVALID_HANDLE)
      {
         PrintFormat("[%s] FileOpen failed for %s — error %d", m_strategy_name, filename, GetLastError());
         return false;
      }

      // Skip header line
      if(!FileIsEnding(handle))
      {
         string hdr = FileReadString(handle);  // datetime_utc
         FileReadString(handle);  // currency
         FileReadString(handle);  // event_name
         FileReadString(handle);  // impact
         FileReadString(handle);  // actual
         FileReadString(handle);  // forecast
         FileReadString(handle);  // previous
      }

      int count = 0;
      while(!FileIsEnding(handle))
      {
         string dt_str   = FileReadString(handle);
         string curr     = FileReadString(handle);
         string evt_name = FileReadString(handle);
         string impact   = FileReadString(handle);
         FileReadString(handle);  // actual — skip
         FileReadString(handle);  // forecast — skip
         FileReadString(handle);  // previous — skip

         if(StringLen(dt_str) < 10 || StringLen(curr) == 0) continue;

         int idx = ArraySize(m_csv_events);
         ArrayResize(m_csv_events, idx + 1, 1000);
         m_csv_events[idx].event_time = StringToTime(dt_str);
         m_csv_events[idx].currency   = curr;
         m_csv_events[idx].event_name = evt_name;
         m_csv_events[idx].impact     = impact;
         count++;
      }
      FileClose(handle);
      m_csv_scan_idx = 0;
      ArrayResize(m_csv_traded, count);
      ArrayInitialize(m_csv_traded, false);
      return (count > 0);
   }

   //+------------------------------------------------------------------+
   //| Check CSV events in Strategy Tester mode                         |
   //| Each event fires AT MOST ONCE per backtest — tracked by index.   |
   //| We wait 2-5 minutes after the event for the spike to develop,    |
   //| then enter if the threshold is met.                              |
   //+------------------------------------------------------------------+
   void CheckCSVEvents(datetime now)
   {
      int total = ArraySize(m_csv_events);
      if(total == 0) return;

      int min_age = 2 * 60;    // Wait 2 min for spike to develop
      int max_age = 15 * 60;   // Give up after 15 min

      // Advance scan index past events too old to matter
      while(m_csv_scan_idx < total && m_csv_events[m_csv_scan_idx].event_time < now - max_age)
         m_csv_scan_idx++;

      string chart_sym = _Symbol;

      for(int i = m_csv_scan_idx; i < total; i++)
      {
         datetime evt_time = m_csv_events[i].event_time;
         if(evt_time > now) break;

         // Already traded this event — skip permanently
         if(m_csv_traded[i]) continue;

         int age_sec = (int)(now - evt_time);
         if(age_sec < min_age || age_sec > max_age) continue;

         string currency = m_csv_events[i].currency;

         if(StringFind(chart_sym, currency) < 0 &&
            !IsCurrencyInPair(chart_sym, currency))
            continue;

         // Attempt entry — mark as traded regardless of outcome
         // (if spike is too small now, it won't grow later)
         m_csv_traded[i] = true;
         EvaluateAndTrade(chart_sym, currency, evt_time, m_csv_events[i].event_name);
      }
   }

   //+------------------------------------------------------------------+
   //| Check if a currency is base or quote of a pair                    |
   //+------------------------------------------------------------------+
   bool IsCurrencyInPair(string pair, string currency)
   {
      // Standard forex pairs: 6-char, e.g. EURUSD → base=EUR, quote=USD
      if(StringLen(pair) >= 6)
      {
         string base = StringSubstr(pair, 0, 3);
         string quote = StringSubstr(pair, 3, 3);
         if(base == currency || quote == currency) return true;
      }
      return false;
   }

   //+------------------------------------------------------------------+
   //| Get affected pairs for a currency                                |
   //+------------------------------------------------------------------+
   void GetAffectedPairs(string currency, string &pairs[])
   {
      for(int i = 0; i < ArraySize(m_pair_map); i++)
      {
         if(m_pair_map[i].currency == currency)
         {
            ArrayResize(pairs, ArraySize(m_pair_map[i].pairs));
            for(int j = 0; j < ArraySize(m_pair_map[i].pairs); j++)
               pairs[j] = m_pair_map[i].pairs[j];
            return;
         }
      }
      ArrayResize(pairs, 0);
   }

   //+------------------------------------------------------------------+
   //| Check if we already traded this event on this symbol             |
   //| Uses a tighter time window to avoid blocking distinct events.    |
   //+------------------------------------------------------------------+
   bool HasRecentPosition(string currency, datetime event_time)
   {
      int window = m_is_tester ? 5 * 60 : 20 * 60;

      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         if(PositionSelectByTicket(PositionGetTicket(i)))
         {
            if(PositionGetInteger(POSITION_MAGIC) == m_magic)
            {
               datetime open_time = (datetime)PositionGetInteger(POSITION_TIME);
               if(MathAbs((double)(open_time - event_time)) < window)
                  return true;
            }
         }
      }

      // Also check recent closed trades (history) so we don't re-enter
      // after a quick SL hit
      if(HistorySelect(event_time - window, event_time + window))
      {
         for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
         {
            ulong ticket = HistoryDealGetTicket(i);
            if(ticket > 0 && HistoryDealGetInteger(ticket, DEAL_MAGIC) == m_magic)
            {
               if(HistoryDealGetInteger(ticket, DEAL_ENTRY) == DEAL_ENTRY_IN)
                  return true;
            }
         }
      }

      return false;
   }

   //+------------------------------------------------------------------+
   //| Core evaluation: measure spike, apply filters, enter trade       |
   //+------------------------------------------------------------------+
   void EvaluateAndTrade(string symbol, string currency, datetime event_time, string event_name)
   {
      if(!SymbolSelect(symbol, true))
      {
         if(m_is_tester)
            PrintFormat("[%s] SKIP %s: symbol not available in tester", m_strategy_name, symbol);
         return;
      }

      // --- Measure the post-event spike (price move since event) ---
      double price_at_event = GetPriceAtTime(symbol, event_time);
      double price_now = SymbolInfoDouble(symbol, SYMBOL_BID);
      if(price_at_event == 0 || price_now == 0)
      {
         if(m_is_tester && price_at_event == 0)
            PrintFormat("[%s] SKIP %s: no price data at event time %s",
                        m_strategy_name, symbol, TimeToString(event_time));
         return;
      }

      double pip = PipSize(symbol);
      double spike_pips = (price_now - price_at_event) / pip;
      double abs_spike = MathAbs(spike_pips);

      // In tester mode, scale down spike thresholds — single-pair measurement
      // captures less of the move than the cross-pair aggregate used in research
      double effective_threshold = m_spike_threshold;
      if(m_is_tester && m_spike_threshold > 0)
         effective_threshold = m_spike_threshold * m_tester_spike_scale;

      // Spike threshold filter
      if(abs_spike < effective_threshold)
      {
         if(m_is_tester && effective_threshold > 0)
            PrintFormat("[%s] SKIP %s: spike %.1f pips < threshold %.0f (scaled from %.0f) after '%s'",
                        m_strategy_name, symbol, abs_spike, effective_threshold, m_spike_threshold, event_name);
         return;
      }

      // --- Apply strategy-specific filters ---
      if(!PassesFilters(symbol, event_time))
      {
         if(m_is_tester)
            PrintFormat("[%s] SKIP %s: filter blocked (spike=%.1f) after '%s'",
                        m_strategy_name, symbol, spike_pips, event_name);
         return;
      }

      // --- Determine entry direction based on strategy ---
      ENUM_ORDER_TYPE order_type;
      double entry_price, sl, tp;
      double point = PipPoint(symbol);

      if(m_use_bb_breakout)
      {
         // BB breakout: trade in direction of breakout
         order_type = (spike_pips > 0) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      }
      else
      {
         // Fade strategy: trade AGAINST the spike (mean reversion)
         order_type = (spike_pips > 0) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
      }

      if(order_type == ORDER_TYPE_BUY)
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

      string comment = StringFormat("%s|%s|%s|%.0fpip",
                                     m_strategy_name, event_name, currency, spike_pips);

      double lots = CalculateLotSize(symbol);

      if(m_trade.PositionOpen(symbol, order_type, lots, entry_price, sl, tp, comment))
      {
         PrintFormat("[%s] TRADE: %s %s %.2f lots (%.0f EUR notional) on %s event '%s' (spike=%.1f pips)",
                     m_strategy_name,
                     (order_type == ORDER_TYPE_BUY) ? "BUY" : "SELL",
                     symbol, lots, m_notional_eur, currency, event_name, spike_pips);
      }
      else
      {
         PrintFormat("[%s] TRADE FAILED: %s %s — error %d: %s",
                     m_strategy_name, symbol,
                     (order_type == ORDER_TYPE_BUY) ? "BUY" : "SELL",
                     m_trade.ResultRetcode(), m_trade.ResultComment());
      }
   }

   //+------------------------------------------------------------------+
   //| Apply all configured filters                                     |
   //| In Strategy Tester mode, cross-symbol data (VIX, gold) is not    |
   //| available — skip those filters rather than blocking all trades.   |
   //| Volume data IS available for the chart symbol in Tester mode.     |
   //+------------------------------------------------------------------+
   bool PassesFilters(string symbol, datetime event_time)
   {
      // --- VIX filter ---
      // In tester: VIX data not available, ATR approximation unreliable — bypass
      if(m_use_vix_filter && !m_is_tester)
      {
         double vix = GetVIXLevel();
         if(vix > 0)
         {
            if(m_vix_below && vix > m_vix_threshold)
               return false;
            if(!m_vix_below && vix < m_vix_threshold)
               return false;
         }
      }

      // --- Volume ratio filter ---
      // In tester: tick volume is synthetic and unreliable — bypass entirely
      if(m_use_volume_filter && !m_is_tester)
      {
         double vol_ratio = GetVolumeRatio(symbol, 20);

         if(m_volume_above && vol_ratio < m_volume_threshold) return false;
         if(!m_volume_above && vol_ratio > m_volume_threshold) return false;
      }

      // --- Gold correlation filter ---
      // In tester: XAUUSD data typically unavailable — bypass
      if(m_use_gold_filter && !m_is_tester)
      {
         double gold_corr = GetGoldCorrelation(symbol, 20);
         if(gold_corr != 0)
         {
            if(m_gold_negative_corr && gold_corr > -0.3) return false;
            if(!m_gold_negative_corr && gold_corr < 0.3) return false;
         }
      }

      // --- Volatility regime filter (ATR percentile) ---
      // In tester: relax thresholds since single-pair ATR is noisier
      if(m_use_vol_regime)
      {
         double atr_pct = GetATRPercentile(symbol, 100);
         double high_thresh = m_is_tester ? 0.40 : 0.67;
         double low_thresh  = m_is_tester ? 0.60 : 0.33;
         if(m_vol_regime_target == "high_only" && atr_pct < high_thresh) return false;
         if(m_vol_regime_target == "low_only" && atr_pct > low_thresh) return false;
      }

      // --- Mean reversion gate (price must be near BB extremes) ---
      if(m_use_mean_rev_gate)
      {
         double bb_pos = GetBBPosition(symbol);
         if(bb_pos > 0.2 && bb_pos < 0.8) return false;  // Only trade at extremes
      }

      return true;
   }

   //+------------------------------------------------------------------+
   //| Get price at a specific historical time                          |
   //| Always uses M1 for spike measurement accuracy — the strategy     |
   //| timeframe (M5/M15/H1) is too coarse for event-time prices.      |
   //+------------------------------------------------------------------+
   double GetPriceAtTime(string symbol, datetime target_time)
   {
      MqlRates rates[];
      // Try M1 first for best precision
      if(CopyRates(symbol, PERIOD_M1, target_time, 1, rates) > 0)
         return rates[0].close;
      // Fall back to M5 if M1 unavailable
      if(CopyRates(symbol, PERIOD_M5, target_time, 1, rates) > 0)
         return rates[0].close;
      // Last resort: strategy timeframe
      if(CopyRates(symbol, m_timeframe, target_time, 1, rates) > 0)
         return rates[0].close;
      return 0;
   }

   //+------------------------------------------------------------------+
   //| Volume ratio: current tick volume / 20-bar average               |
   //+------------------------------------------------------------------+
   double GetVolumeRatio(string symbol, int period)
   {
      long volumes[];
      if(CopyTickVolume(symbol, m_timeframe, 0, period + 1, volumes) < period + 1)
         return 1.0;

      double avg = 0;
      for(int i = 0; i < period; i++)
         avg += (double)volumes[i];
      avg /= period;

      if(avg <= 0) return 1.0;
      return (double)volumes[period] / avg;
   }

   //+------------------------------------------------------------------+
   //| VIX level: try common broker symbol names                        |
   //+------------------------------------------------------------------+
   double GetVIXLevel()
   {
      string vix_symbols[] = {"VIX", "VIX.cash", "VOLATILITY", "VIX_INDEX", "US500VOL"};
      for(int i = 0; i < ArraySize(vix_symbols); i++)
      {
         if(SymbolSelect(vix_symbols[i], true))
         {
            double bid = SymbolInfoDouble(vix_symbols[i], SYMBOL_BID);
            if(bid > 0) return bid;
         }
      }
      // Fallback: approximate from ATR expansion across majors
      return ApproximateVIX();
   }

   //+------------------------------------------------------------------+
   //| Approximate VIX from major pair ATR (broker-independent fallback)|
   //+------------------------------------------------------------------+
   double ApproximateVIX()
   {
      // Compute normalized ATR across EURUSD, GBPUSD, USDJPY
      // Map to approximate VIX range (12-40)
      string majors[] = {"EURUSD", "GBPUSD", "USDJPY"};
      double total_atr_pct = 0;
      int count = 0;

      for(int i = 0; i < ArraySize(majors); i++)
      {
         int atr_h = GetATRHandle(majors[i]);
         if(atr_h == INVALID_HANDLE) continue;

         double atr_val[];
         if(CopyBuffer(atr_h, 0, 0, 1, atr_val) > 0)
         {
            double price = SymbolInfoDouble(majors[i], SYMBOL_BID);
            if(price > 0)
            {
               total_atr_pct += atr_val[0] / price * 100;
               count++;
            }
         }
      }

      if(count == 0) return 20.0;  // Neutral default
      double avg_atr_pct = total_atr_pct / count;
      // Empirical mapping: avg ATR% 0.03 ≈ VIX 12, ATR% 0.12 ≈ VIX 40
      return 12.0 + (avg_atr_pct - 0.03) / (0.12 - 0.03) * 28.0;
   }

   //+------------------------------------------------------------------+
   //| Gold correlation: 20-bar rolling correlation with XAUUSD         |
   //+------------------------------------------------------------------+
   double GetGoldCorrelation(string symbol, int period)
   {
      string gold_sym = "XAUUSD";
      if(!SymbolSelect(gold_sym, true))
      {
         gold_sym = "GOLD";
         if(!SymbolSelect(gold_sym, true)) return 0;
      }

      double sym_close[], gold_close[];
      if(CopyClose(symbol, m_timeframe, 0, period, sym_close) < period) return 0;
      if(CopyClose(gold_sym, m_timeframe, 0, period, gold_close) < period) return 0;

      // Compute Pearson correlation on returns
      double sym_ret[], gold_ret[];
      ArrayResize(sym_ret, period - 1);
      ArrayResize(gold_ret, period - 1);

      for(int i = 1; i < period; i++)
      {
         sym_ret[i-1] = (sym_close[i] - sym_close[i-1]) / sym_close[i-1];
         gold_ret[i-1] = (gold_close[i] - gold_close[i-1]) / gold_close[i-1];
      }

      int n = period - 1;
      double sum_x=0, sum_y=0, sum_xy=0, sum_x2=0, sum_y2=0;
      for(int i = 0; i < n; i++)
      {
         sum_x += sym_ret[i];
         sum_y += gold_ret[i];
         sum_xy += sym_ret[i] * gold_ret[i];
         sum_x2 += sym_ret[i] * sym_ret[i];
         sum_y2 += gold_ret[i] * gold_ret[i];
      }

      double denom = MathSqrt((n*sum_x2 - sum_x*sum_x) * (n*sum_y2 - sum_y*sum_y));
      if(denom == 0) return 0;
      return (n*sum_xy - sum_x*sum_y) / denom;
   }

   //+------------------------------------------------------------------+
   //| ATR percentile over lookback period                              |
   //+------------------------------------------------------------------+
   double GetATRPercentile(string symbol, int lookback)
   {
      int atr_h = GetATRHandle(symbol);
      if(atr_h == INVALID_HANDLE) return 0.5;

      double atr_vals[];
      if(CopyBuffer(atr_h, 0, 0, lookback, atr_vals) < lookback) return 0.5;

      double current = atr_vals[lookback - 1];
      int below = 0;
      for(int i = 0; i < lookback; i++)
         if(atr_vals[i] < current) below++;

      return (double)below / lookback;
   }

   //+------------------------------------------------------------------+
   //| Bollinger Band position: (price - lower) / (upper - lower)       |
   //+------------------------------------------------------------------+
   double GetBBPosition(string symbol)
   {
      int bb_h = GetBBHandle(symbol);
      if(bb_h == INVALID_HANDLE) return 0.5;

      double upper[], lower[];
      if(CopyBuffer(bb_h, 1, 0, 1, upper) < 1) return 0.5;  // Upper band
      if(CopyBuffer(bb_h, 2, 0, 1, lower) < 1) return 0.5;  // Lower band

      double price = SymbolInfoDouble(symbol, SYMBOL_BID);
      double range = upper[0] - lower[0];
      if(range <= 0) return 0.5;

      return (price - lower[0]) / range;
   }
};
