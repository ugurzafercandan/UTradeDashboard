//+------------------------------------------------------------------+
//| KillLosers.mq5                                                   |
//| USO-469: Close all positions and orders for 15 losing signals     |
//|                                                                  |
//| RUN AS A SCRIPT (not an EA). Drag onto any chart from Navigator  |
//| > Scripts. It executes once and reports results.                   |
//+------------------------------------------------------------------+
#property copyright "USO-469 Board Optimization"
#property version   "1.00"
#property script_show_inputs

#include <Trade\Trade.mqh>

input bool InpDryRun = true; // Dry run (true = report only, false = close positions)

const int KILL_MAGICS[] =
{
   208014, // P14 GBPCAD   -$2661.86
   208015, // P15 XAUUSD   -$767.22
   208016, // P16 USDCAD   -$1087.34
   208021, // P21 XAUUSD   -$861.48
   208022, // P22 XAUUSD   -$81.82
   208023, // P23 XAUUSD   -$839.00
   208030, // P30 EURGBP   -$6154.88
   208031, // P31 AUDNZD   -$252.53
   208032, // P32 GBPCAD   -$1534.68
   208033, // P33 EURCHF   -$409.60
   208034, // P34 EURGBP   -$5859.49
   208036, // P36 EURGBP   -$6142.30
   208038, // P38 EURCHF   -$1605.25
   208044, // P44 USDJPY   -$267.25
   208046  // P46 USDCAD   -$2748.98
};

bool IsKillMagic(long magic)
{
   for(int i = 0; i < ArraySize(KILL_MAGICS); i++)
      if(KILL_MAGICS[i] == magic)
         return true;
   return false;
}

void OnStart()
{
   CTrade trade;
   trade.SetDeviationInPoints(30);
   trade.SetTypeFilling(ORDER_FILLING_IOC);

   PrintFormat("=== KillLosers %s ===", InpDryRun ? "DRY RUN" : "LIVE");
   PrintFormat("Scanning for positions/orders matching %d losing magic numbers...",
               ArraySize(KILL_MAGICS));

   int pos_closed = 0;
   int pos_failed = 0;
   double total_pnl = 0.0;

   //--- Close open positions ---
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;

      long magic = PositionGetInteger(POSITION_MAGIC);
      if(!IsKillMagic(magic)) continue;

      string symbol = PositionGetString(POSITION_SYMBOL);
      double profit = PositionGetDouble(POSITION_PROFIT) +
                      PositionGetDouble(POSITION_SWAP);
      double volume = PositionGetDouble(POSITION_VOLUME);
      long type = PositionGetInteger(POSITION_TYPE);
      string dir = (type == POSITION_TYPE_BUY) ? "BUY" : "SELL";

      PrintFormat("  POSITION #%I64u: %s %s %.2f lots, magic=%d, P&L=%.2f",
                  ticket, dir, symbol, volume, magic, profit);

      if(!InpDryRun)
      {
         trade.SetExpertMagicNumber((int)magic);
         if(trade.PositionClose(ticket))
         {
            PrintFormat("    -> CLOSED OK");
            pos_closed++;
            total_pnl += profit;
         }
         else
         {
            PrintFormat("    -> CLOSE FAILED: %d %s",
                        trade.ResultRetcode(), trade.ResultComment());
            pos_failed++;
         }
      }
      else
      {
         pos_closed++;
         total_pnl += profit;
      }
   }

   //--- Remove pending orders ---
   int ord_deleted = 0;
   int ord_failed = 0;

   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket == 0) continue;

      long magic = OrderGetInteger(ORDER_MAGIC);
      if(!IsKillMagic(magic)) continue;

      string symbol = OrderGetString(ORDER_SYMBOL);
      long type = OrderGetInteger(ORDER_TYPE);

      PrintFormat("  ORDER #%I64u: type=%d %s, magic=%d",
                  ticket, type, symbol, magic);

      if(!InpDryRun)
      {
         if(trade.OrderDelete(ticket))
         {
            PrintFormat("    -> DELETED OK");
            ord_deleted++;
         }
         else
         {
            PrintFormat("    -> DELETE FAILED: %d %s",
                        trade.ResultRetcode(), trade.ResultComment());
            ord_failed++;
         }
      }
      else
      {
         ord_deleted++;
      }
   }

   //--- Summary ---
   PrintFormat("");
   PrintFormat("=== SUMMARY (%s) ===", InpDryRun ? "DRY RUN" : "LIVE");
   PrintFormat("Positions %s: %d (failed: %d)",
               InpDryRun ? "found" : "closed", pos_closed, pos_failed);
   PrintFormat("Orders %s: %d (failed: %d)",
               InpDryRun ? "found" : "deleted", ord_deleted, ord_failed);
   PrintFormat("Unrealized P&L on closed positions: $%.2f", total_pnl);

   if(InpDryRun && (pos_closed > 0 || ord_deleted > 0))
      PrintFormat("\n** Set InpDryRun=false and run again to execute closes **");

   if(!InpDryRun && pos_closed == 0 && ord_deleted == 0)
      PrintFormat("No matching positions or orders found — all clean.");

   PrintFormat("=== KillLosers complete ===");
}
//+------------------------------------------------------------------+
