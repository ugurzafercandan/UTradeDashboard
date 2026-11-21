//+------------------------------------------------------------------+
//| MLSignalFramework.mqh — Shared framework for ML signal EAs       |
//|                                                                  |
//| Reads JSON signal files from MQL5/Files/ written by the Python   |
//| ML signal server. Each signal gets its own file:                  |
//|   ml_signal_P6.json, ml_signal_P7.json, etc.                     |
//|                                                                  |
//| Unlike NewsTraderFramework.mqh (event-driven), this polls for    |
//| ML model predictions and executes trades based on direction,     |
//| confidence threshold, and ATR-based risk management.             |
//+------------------------------------------------------------------+
#property copyright "USO-465 ML Signal Portfolio"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
//| Parsed signal data                                               |
//+------------------------------------------------------------------+
struct MLSignalData
{
   string   signal_id;
   string   symbol;
   string   direction;     // "BUY", "SELL", "HOLD"
   double   confidence;
   string   timestamp;
   double   atr;
   bool     spread_ok;
   bool     valid;
};

//+------------------------------------------------------------------+
//| CMLSignalBase — base class for all ML signal EAs                 |
//+------------------------------------------------------------------+
class CMLSignalBase
{
protected:
   CTrade         m_trade;
   int            m_magic;
   string         m_signal_id;
   string         m_signal_file;       // e.g. "ml_signal_P6.json"
   string         m_broker_suffix;     // B3: broker symbol suffix (e.g. ".m", "_ecn", "")
   double         m_lot_size;          // Fallback fixed lot
   double         m_notional_eur;      // Target notional per trade in EUR
   double         m_risk_pct;          // Risk per trade (1-2%)
   double         m_kelly_cap;         // 0.25 = 25% of full Kelly
   double         m_sl_atr_mult;       // SL = ATR * this
   double         m_tp_atr_mult;       // TP = ATR * this
   string         m_exit_method;       // "simple" or "triple_barrier"
   int            m_timeout_bars;      // Triple-barrier timeout in bars
   double         m_entry_threshold;   // Minimum confidence to enter

   // Signal state
   datetime       m_last_signal_time;
   datetime       m_last_file_mod;
   datetime       m_last_file_check;
   MLSignalData   m_current_signal;

   // Position tracking
   bool           m_has_position;
   ulong          m_position_ticket;
   datetime       m_position_open_time;
   int            m_position_bars;
   int            m_position_bar_count;

public:
   CMLSignalBase()
   {
      m_magic = 0;
      m_signal_id = "";
      m_signal_file = "";
      m_broker_suffix = "";
      m_lot_size = 0.01;
      m_notional_eur = 1000.0;
      m_risk_pct = 1.5;
      m_kelly_cap = 0.25;
      m_sl_atr_mult = 1.5;
      m_tp_atr_mult = 2.0;
      m_exit_method = "simple";
      m_timeout_bars = 120;
      m_entry_threshold = 0.55;
      m_last_signal_time = 0;
      m_last_file_mod = 0;
      m_last_file_check = 0;
      m_has_position = false;
      m_position_ticket = 0;
      m_position_open_time = 0;
      m_position_bars = 0;
      m_position_bar_count = 0;
      m_current_signal.valid = false;
   }

   //+--------------------------------------------------------------+
   //| Initialize the EA with signal configuration                   |
   //+--------------------------------------------------------------+
   bool Initialize(int magic, string signal_id, double notional_eur,
                   double risk_pct, double sl_mult, double tp_mult,
                   string exit_method, int timeout_bars, double entry_threshold,
                   string broker_suffix = "")
   {
      m_magic = magic;
      m_signal_id = signal_id;
      m_signal_file = "ml_signal_" + signal_id + ".json";
      // B3 fix: store broker symbol suffix so CalculateLots/EURNormalizedLots
      // can resolve broker-specific names like EURUSD.m.
      // SymbolInfoDouble on a bare "EURUSD" returns 0 when the broker requires
      // "EURUSD.m", causing CalculateLots to silently return 0 (no trade placed).
      m_broker_suffix = broker_suffix;
      m_notional_eur = notional_eur;
      m_risk_pct = MathMin(risk_pct, 3.0);
      m_sl_atr_mult = sl_mult;
      m_tp_atr_mult = tp_mult;
      m_exit_method = exit_method;
      m_timeout_bars = timeout_bars;
      m_entry_threshold = entry_threshold;

      m_trade.SetExpertMagicNumber(magic);
      m_trade.SetDeviationInPoints(20);
      m_trade.SetTypeFilling(ORDER_FILLING_IOC);

      PrintFormat("[%s] Initialized: magic=%d, notional=%.0f EUR, risk=%.1f%%, "
                  "SL=ATR*%.1f, TP=ATR*%.1f, exit=%s, timeout=%d bars, ET=%.2f",
                  m_signal_id, m_magic, m_notional_eur, m_risk_pct,
                  m_sl_atr_mult, m_tp_atr_mult, m_exit_method, m_timeout_bars,
                  m_entry_threshold);
      return true;
   }

   //+--------------------------------------------------------------+
   //| Main tick handler                                             |
   //+--------------------------------------------------------------+
   void OnTickHandler()
   {
      // Refresh position state
      RefreshPositionState();

      // Manage existing positions (triple-barrier timeout check)
      if(m_has_position && m_exit_method == "triple_barrier")
         ManageTripleBarrier();

      // Poll signal file (at most once per second)
      datetime now = TimeCurrent();
      if(now - m_last_file_check < 1)
         return;
      m_last_file_check = now;

      // Read and parse signal file
      if(!ReadSignalFile())
         return;

      // Skip if we already have a position for this signal
      if(m_has_position)
         return;

      // Skip HOLD signals
      if(m_current_signal.direction == "HOLD")
         return;

      // Check confidence threshold
      if(m_current_signal.confidence < m_entry_threshold)
         return;

      // Check spread
      if(!m_current_signal.spread_ok)
      {
         PrintFormat("[%s] Spread too wide, skipping entry", m_signal_id);
         return;
      }

      // Execute the signal
      ExecuteSignal(m_current_signal.direction,
                    m_current_signal.confidence,
                    m_current_signal.atr);
   }

   //+--------------------------------------------------------------+
   //| Cleanup                                                       |
   //+--------------------------------------------------------------+
   void Cleanup()
   {
      PrintFormat("[%s] EA deinitialized", m_signal_id);
   }

private:
   //+--------------------------------------------------------------+
   //| Read signal file if it has been modified                      |
   //+--------------------------------------------------------------+
   bool ReadSignalFile()
   {
      // Check if file exists and has been modified
      // NOTE: MQL5 has no FileGetDate(); use FileGetInteger(FILE_MODIFY_DATE)
      // on a read-only handle instead (UGT-42 compile fix).
      long file_date = -1;
      {
         int h = FileOpen(m_signal_file, FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_SHARE_WRITE);
         if(h != INVALID_HANDLE)
         {
            file_date = FileGetInteger(h, FILE_MODIFY_DATE);
            FileClose(h);
         }
      }
      if(file_date < 0)
         return false;

      datetime mod_time = (datetime)file_date;
      if(mod_time == m_last_file_mod)
         return false;  // No change

      // Read file contents
      string content = ReadFileContents(m_signal_file);
      if(content == "")
         return false;

      m_last_file_mod = mod_time;

      // Parse JSON
      if(!ParseSignalJSON(content))
         return false;

      // Verify signal ID matches
      if(m_current_signal.signal_id != m_signal_id)
      {
         PrintFormat("[%s] Signal ID mismatch: expected %s, got %s",
                     m_signal_id, m_signal_id, m_current_signal.signal_id);
         m_current_signal.valid = false;
         return false;
      }

      return m_current_signal.valid;
   }

   //+--------------------------------------------------------------+
   //| Read entire file contents as a string                         |
   //+--------------------------------------------------------------+
   string ReadFileContents(string filename)
   {
      int handle = FileOpen(filename, FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
      if(handle == INVALID_HANDLE)
         return "";

      string content = "";
      while(!FileIsEnding(handle))
      {
         content += FileReadString(handle);
      }
      FileClose(handle);
      return content;
   }

   //+--------------------------------------------------------------+
   //| Parse flat JSON signal into MLSignalData                      |
   //| Format: {"signal_id":"P6","symbol":"AUDCHF",...}              |
   //+--------------------------------------------------------------+
   bool ParseSignalJSON(string json)
   {
      m_current_signal.valid = false;

      m_current_signal.signal_id  = ExtractStringValue(json, "signal_id");
      m_current_signal.symbol     = ExtractStringValue(json, "symbol");
      m_current_signal.direction  = ExtractStringValue(json, "direction");
      m_current_signal.timestamp  = ExtractStringValue(json, "timestamp");
      m_current_signal.confidence = ExtractDoubleValue(json, "confidence");
      m_current_signal.atr        = ExtractDoubleValue(json, "atr");
      m_current_signal.spread_ok  = ExtractBoolValue(json, "spread_ok");

      if(m_current_signal.signal_id == "" || m_current_signal.symbol == "" ||
         m_current_signal.direction == "")
         return false;

      if(m_current_signal.atr <= 0)
         return false;

      m_current_signal.valid = true;
      return true;
   }

   //+--------------------------------------------------------------+
   //| Extract a quoted string value for a given key from JSON       |
   //+--------------------------------------------------------------+
   string ExtractStringValue(const string &json, const string key)
   {
      string search = "\"" + key + "\"";
      int pos = StringFind(json, search);
      if(pos < 0)
         return "";

      // Find the colon after the key
      int colon = StringFind(json, ":", pos + StringLen(search));
      if(colon < 0)
         return "";

      // Skip whitespace after colon
      int start = colon + 1;
      while(start < StringLen(json) && (StringGetCharacter(json, start) == ' '))
         start++;

      // Check if value is a quoted string
      if(StringGetCharacter(json, start) != '"')
         return "";

      start++; // skip opening quote
      int end = StringFind(json, "\"", start);
      if(end < 0)
         return "";

      return StringSubstr(json, start, end - start);
   }

   //+--------------------------------------------------------------+
   //| Extract a numeric value for a given key from JSON             |
   //+--------------------------------------------------------------+
   double ExtractDoubleValue(const string &json, const string key)
   {
      string search = "\"" + key + "\"";
      int pos = StringFind(json, search);
      if(pos < 0)
         return 0.0;

      int colon = StringFind(json, ":", pos + StringLen(search));
      if(colon < 0)
         return 0.0;

      // Extract the numeric portion after the colon
      int start = colon + 1;
      while(start < StringLen(json) && StringGetCharacter(json, start) == ' ')
         start++;

      int end = start;
      while(end < StringLen(json))
      {
         ushort ch = StringGetCharacter(json, end);
         if(ch == ',' || ch == '}' || ch == ' ' || ch == '\n' || ch == '\r')
            break;
         end++;
      }

      string val = StringSubstr(json, start, end - start);
      return StringToDouble(val);
   }

   //+--------------------------------------------------------------+
   //| Extract a boolean value for a given key from JSON             |
   //+--------------------------------------------------------------+
   bool ExtractBoolValue(const string &json, const string key)
   {
      string search = "\"" + key + "\"";
      int pos = StringFind(json, search);
      if(pos < 0)
         return false;

      int colon = StringFind(json, ":", pos + StringLen(search));
      if(colon < 0)
         return false;

      int start = colon + 1;
      while(start < StringLen(json) && StringGetCharacter(json, start) == ' ')
         start++;

      // Check for "true"
      if(StringFind(json, "true", start) == start)
         return true;

      return false;
   }

   //+--------------------------------------------------------------+
   //| Calculate lot size using fixed fractional + Kelly cap         |
   //+--------------------------------------------------------------+
   double CalculateLots(string symbol, double sl_points)
   {
      if(sl_points <= 0)
         return 0.0;

      double equity = AccountInfoDouble(ACCOUNT_EQUITY);
      if(equity <= 0)
         return 0.0;

      // Fixed fractional: risk m_risk_pct of equity
      double risk_amount = equity * (m_risk_pct / 100.0);

      // Apply Kelly cap: cap risk at kelly_cap * equity
      double kelly_max = equity * m_kelly_cap;
      risk_amount = MathMin(risk_amount, kelly_max);

      // Get symbol tick info
      double tick_value = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
      double tick_size  = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);

      if(tick_value <= 0 || tick_size <= 0)
         return 0.0;

      double ticks_at_risk = sl_points / tick_size;
      double risk_per_lot  = ticks_at_risk * tick_value;

      if(risk_per_lot <= 0)
         return 0.0;

      double lots_from_risk = risk_amount / risk_per_lot;

      // EUR-normalized lot sizing
      double lots_from_notional = EURNormalizedLots(symbol);

      // Use the smaller of risk-based and notional-based sizing
      double raw_lots = MathMin(lots_from_risk, lots_from_notional);

      // Round to symbol lot step
      double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
      double lot_min  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
      double lot_max  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);

      if(lot_step <= 0) lot_step = 0.01;
      if(lot_min  <= 0) lot_min  = 0.01;

      double lots = MathFloor(raw_lots / lot_step) * lot_step;
      lots = NormalizeDouble(lots, 2);

      if(lots < lot_min)
         return 0.0;
      if(lots > lot_max)
         lots = lot_max;

      return lots;
   }

   //+--------------------------------------------------------------+
   //| EUR-normalized lot sizing                                     |
   //+--------------------------------------------------------------+
   double EURNormalizedLots(string symbol)
   {
      if(m_notional_eur <= 0)
         return 10.0;  // No notional cap

      double contract_size = SymbolInfoDouble(symbol, SYMBOL_TRADE_CONTRACT_SIZE);
      if(contract_size <= 0)
         contract_size = 100000.0;

      // Get price in account currency terms
      double price = SymbolInfoDouble(symbol, SYMBOL_BID);
      if(price <= 0)
         price = SymbolInfoDouble(symbol, SYMBOL_ASK);
      if(price <= 0)
         return 0.01;

      // Determine conversion to EUR
      string account_currency = AccountInfoString(ACCOUNT_CURRENCY);
      double conversion = 1.0;

      if(account_currency == "EUR")
      {
         // Base currency of the symbol
         string base_currency = SymbolInfoString(symbol, SYMBOL_CURRENCY_BASE);
         if(base_currency == "EUR")
            conversion = 1.0;
         else
         {
            // Try EURUSD (with broker suffix) to get EUR value
            string eurusd_sym = "EURUSD" + m_broker_suffix;
            double eurusd = 0;
            if(SymbolInfoDouble(eurusd_sym, SYMBOL_BID) > 0)
               eurusd = SymbolInfoDouble(eurusd_sym, SYMBOL_BID);
            else
               eurusd = 1.10;  // Fallback

            if(base_currency == "USD")
               conversion = 1.0 / eurusd;
            else if(base_currency == "GBP")
            {
               double gbpusd = SymbolInfoDouble("GBPUSD" + m_broker_suffix, SYMBOL_BID);
               if(gbpusd <= 0) gbpusd = 1.27;
               conversion = gbpusd / eurusd;
            }
            else if(base_currency == "AUD")
            {
               double audusd = SymbolInfoDouble("AUDUSD" + m_broker_suffix, SYMBOL_BID);
               if(audusd <= 0) audusd = 0.65;
               conversion = audusd / eurusd;
            }
            else if(base_currency == "NZD")
            {
               double nzdusd = SymbolInfoDouble("NZDUSD" + m_broker_suffix, SYMBOL_BID);
               if(nzdusd <= 0) nzdusd = 0.60;
               conversion = nzdusd / eurusd;
            }
            else if(base_currency == "CAD")
            {
               double usdcad = SymbolInfoDouble("USDCAD" + m_broker_suffix, SYMBOL_BID);
               if(usdcad <= 0) usdcad = 1.37;
               conversion = 1.0 / (usdcad * eurusd);
            }
            else if(base_currency == "CHF")
            {
               double usdchf = SymbolInfoDouble("USDCHF" + m_broker_suffix, SYMBOL_BID);
               if(usdchf <= 0) usdchf = 0.88;
               conversion = 1.0 / (usdchf * eurusd);
            }
            else if(base_currency == "JPY")
            {
               double usdjpy = SymbolInfoDouble("USDJPY" + m_broker_suffix, SYMBOL_BID);
               if(usdjpy <= 0) usdjpy = 150.0;
               conversion = 1.0 / (usdjpy * eurusd);
            }
            else
               conversion = 1.0;
         }
      }
      else
      {
         conversion = price;  // Approximate for non-EUR accounts
      }

      double notional_per_lot = contract_size * conversion;
      if(notional_per_lot <= 0)
         return 0.01;

      return m_notional_eur / notional_per_lot;
   }

   //+--------------------------------------------------------------+
   //| Execute a trade signal                                        |
   //+--------------------------------------------------------------+
   void ExecuteSignal(string direction, double confidence, double atr)
   {
      string symbol = m_current_signal.symbol + m_broker_suffix;

      // Verify symbol is available
      if(!SymbolSelect(symbol, true))
      {
         PrintFormat("[%s] Cannot select symbol %s (suffix='%s')", m_signal_id, symbol, m_broker_suffix);
         return;
      }

      // Convert ATR to points
      double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
      if(point <= 0) return;

      double sl_points = atr * m_sl_atr_mult;
      double tp_points = atr * m_tp_atr_mult;

      // Calculate lot size
      double lots = CalculateLots(symbol, sl_points);
      if(lots <= 0)
      {
         PrintFormat("[%s] Lot calculation returned 0 for %s (SL=%.5f, suffix='%s')",
                     m_signal_id, symbol, sl_points, m_broker_suffix);
         return;
      }

      // Convert price-unit SL/TP to points for order
      double sl_in_points = sl_points / point;
      double tp_in_points = tp_points / point;

      double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
      double bid = SymbolInfoDouble(symbol, SYMBOL_BID);

      bool result = false;

      if(direction == "BUY")
      {
         double sl_price = NormalizeDouble(ask - sl_points, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS));
         double tp_price = NormalizeDouble(ask + tp_points, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS));

         result = m_trade.Buy(lots, symbol, ask, sl_price, tp_price,
                              StringFormat("ML_%s_conf%.2f", m_signal_id, confidence));
      }
      else if(direction == "SELL")
      {
         double sl_price = NormalizeDouble(bid + sl_points, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS));
         double tp_price = NormalizeDouble(bid - tp_points, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS));

         result = m_trade.Sell(lots, symbol, bid, sl_price, tp_price,
                               StringFormat("ML_%s_conf%.2f", m_signal_id, confidence));
      }

      if(result)
      {
         m_has_position = true;
         m_position_ticket = m_trade.ResultDeal();
         m_position_open_time = TimeCurrent();
         m_position_bar_count = 0;

         PrintFormat("[%s] %s %s %.2f lots @ %.5f | SL=%.5f TP=%.5f | conf=%.2f ATR=%.5f",
                     m_signal_id, direction, symbol, lots,
                     (direction == "BUY" ? ask : bid),
                     sl_points, tp_points, confidence, atr);
      }
      else
      {
         PrintFormat("[%s] Trade failed: %s %s %.2f lots — error %d: %s",
                     m_signal_id, direction, symbol, lots,
                     m_trade.ResultRetcode(),
                     m_trade.ResultRetcodeDescription());
      }
   }

   //+--------------------------------------------------------------+
   //| Refresh position state for this magic number                  |
   //+--------------------------------------------------------------+
   void RefreshPositionState()
   {
      m_has_position = false;
      m_position_ticket = 0;

      int total = PositionsTotal();
      for(int i = 0; i < total; i++)
      {
         ulong ticket = PositionGetTicket(i);
         if(ticket == 0) continue;

         if(PositionGetInteger(POSITION_MAGIC) == m_magic)
         {
            m_has_position = true;
            m_position_ticket = ticket;

            // Count bars since open
            if(m_position_open_time > 0)
            {
               datetime open_time = (datetime)PositionGetInteger(POSITION_TIME);
               string symbol = PositionGetString(POSITION_SYMBOL);

               // Use current chart period for bar counting
               int bars_since = iBars(symbol, PERIOD_CURRENT) -
                                iBarShift(symbol, PERIOD_CURRENT, open_time);
               m_position_bar_count = bars_since;
            }
            break;
         }
      }
   }

   //+--------------------------------------------------------------+
   //| Manage triple-barrier exit: timeout check                     |
   //| SL/TP are handled by the broker via order SL/TP levels.       |
   //| This method handles the time barrier (timeout).                |
   //+--------------------------------------------------------------+
   void ManageTripleBarrier()
   {
      if(!m_has_position || m_position_ticket == 0)
         return;

      if(m_position_bar_count >= m_timeout_bars)
      {
         // Time barrier hit — close at market
         if(PositionSelectByTicket(m_position_ticket))
         {
            string symbol = PositionGetString(POSITION_SYMBOL);
            double volume = PositionGetDouble(POSITION_VOLUME);
            long pos_type = PositionGetInteger(POSITION_TYPE);
            double profit = PositionGetDouble(POSITION_PROFIT);

            bool closed = false;
            if(pos_type == POSITION_TYPE_BUY)
               closed = m_trade.Sell(volume, symbol, SymbolInfoDouble(symbol, SYMBOL_BID),
                                     0, 0, StringFormat("ML_%s_timeout", m_signal_id));
            else
               closed = m_trade.Buy(volume, symbol, SymbolInfoDouble(symbol, SYMBOL_ASK),
                                    0, 0, StringFormat("ML_%s_timeout", m_signal_id));

            if(closed)
            {
               PrintFormat("[%s] Triple-barrier TIMEOUT: closed %s after %d bars, PnL=%.2f",
                           m_signal_id, symbol, m_position_bar_count, profit);
               m_has_position = false;
               m_position_ticket = 0;
            }
         }
      }
   }
};
//+------------------------------------------------------------------+
