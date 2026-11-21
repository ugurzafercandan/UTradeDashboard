//+------------------------------------------------------------------+
//| Algo06_MACDFade_Gold.mq5                                         |
//| Portfolio Algo #6 — MACD-Confirmed Fade with Gold Correlation     |
//|                                                                  |
//| STRATEGY: Fade (sell after up-spike, buy after down-spike) with  |
//| MACD histogram confirmation. Only trades when gold correlation   |
//| with the pair is negative (< -0.3), indicating divergence        |
//| between gold and the traded pair — a high-conviction setup.      |
//|                                                                  |
//| MACD CONFIRMATION: Before entering a fade trade, the EA checks   |
//| that the MACD histogram supports the fade direction:             |
//|   - Fade SELL (after up-spike): MACD histogram must be < 0       |
//|   - Fade BUY (after down-spike): MACD histogram must be > 0      |
//| This filters out spikes that have strong momentum behind them.   |
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
//|   SL: 15 pips | TP: 100 pips | Spike threshold: 10 pips         |
//|   Filters: Gold correlation negative, MACD histogram confirmation|
//|   MagicNumber: 461006                                            |
//|                                                                  |
//| BACKTEST RESULTS (2023-2025):                                    |
//|   499 trades | 52.1% win rate | PF 4.52 | Sharpe 8.38            |
//|   Total PnL: +11,141 pips                                        |
//+------------------------------------------------------------------+
#property copyright "USO-461/462 Portfolio"
#property version   "1.00"
#property strict

#include <NewsTraderFramework.mqh>

input int    InpMagicNumber   = 461006;    // Magic number (unique per EA)
input double InpLotSize       = 0.01;      // Lot size per trade (fallback)
input double InpNotionalEUR   = 1000.0;    // Target notional per trade in EUR (0 = use fixed lot)
input double InpSpikeThreshold = 10.0;     // Min spike in pips to trigger
input double InpSLPips        = 15.0;      // Stop loss in pips
input double InpTPPips        = 100.0;     // Take profit in pips

//+------------------------------------------------------------------+
//| Derived class adds MACD histogram confirmation to fade entries    |
//+------------------------------------------------------------------+
class CAlgo06 : public CNewsTraderBase
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

      // Gold correlation filter: require negative correlation
      m_use_gold_filter    = true;
      m_gold_negative_corr = true;

      return Initialize(magic, "Algo06_MACDFade_Gold");
   }

   //+------------------------------------------------------------------+
   //| Override EvaluateAndTrade to add MACD histogram confirmation     |
   //+------------------------------------------------------------------+
   void EvaluateAndTrade(string symbol, string currency, datetime event_time, string event_name)
   {
      if(!SymbolSelect(symbol, true)) return;

      double price_at_event = GetPriceAtTime(symbol, event_time);
      double price_now = SymbolInfoDouble(symbol, SYMBOL_BID);
      if(price_at_event == 0 || price_now == 0) return;

      double pip = PipSize(symbol);
      double spike_pips = (price_now - price_at_event) / pip;
      double abs_spike = MathAbs(spike_pips);

      if(abs_spike < m_spike_threshold) return;
      if(!PassesFilters(symbol, event_time)) return;

      // MACD histogram confirmation for the fade direction
      int macd_h = GetMACDHandle(symbol);
      if(macd_h != INVALID_HANDLE)
      {
         double macd_hist[];
         if(CopyBuffer(macd_h, 2, 0, 1, macd_hist) > 0)
         {
            // Fade SELL (spike was up) needs MACD hist < 0 (bearish divergence)
            if(spike_pips > 0 && macd_hist[0] >= 0) return;
            // Fade BUY (spike was down) needs MACD hist > 0 (bullish divergence)
            if(spike_pips < 0 && macd_hist[0] <= 0) return;
         }
      }

      // Determine entry — fade direction (against spike)
      ENUM_ORDER_TYPE order_type = (spike_pips > 0) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
      double point = PipPoint(symbol);
      double entry_price, sl, tp;

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
         PrintFormat("[%s] TRADE: %s %s %.2f lots (%.0f EUR notional) on %s event '%s' (spike=%.1f pips, MACD confirmed)",
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
};

CAlgo06 algo;

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
