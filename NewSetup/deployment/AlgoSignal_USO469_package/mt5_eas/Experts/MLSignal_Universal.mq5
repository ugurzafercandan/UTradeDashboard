//+------------------------------------------------------------------+
//| MLSignal_Universal.mq5                                           |
//| Universal ML Signal EA — reads predictions from Python signal    |
//| server via JSON files in MQL5/Files/                              |
//|                                                                  |
//| USAGE: Attach one instance per signal to any chart.               |
//| Set InpSignalID to the signal (P6, P7, P8, ..., P32).           |
//| The EA reads ml_signal_{InpSignalID}.json and trades accordingly.|
//|                                                                  |
//| SIGNAL DETAILS (Tier A examples):                                |
//|   P8  CADCHF LightGBM Simple   ET=0.62 Magic=46008              |
//|   P6  AUDCHF XGBoost  Simple   ET=0.65 Magic=46006              |
//|   P7  USDCHF XGBoost  Triple   ET=0.58 Magic=46007              |
//|   P11 GBPCHF XGBoost  Simple   ET=0.60 Magic=46011              |
//|   P16 GBPAUD XGBoost  Simple   ET=0.60 Magic=46016              |
//|   P17 GBPUSD LightGBM Simple   ET=0.60 Magic=46017              |
//|   P18 CHFJPY XGBoost  Simple   ET=0.60 Magic=46018              |
//+------------------------------------------------------------------+
#property copyright "USO-465 ML Signal Portfolio"
#property version   "1.00"
#property strict

#include <MLSignalFramework.mqh>

//--- Input parameters
input string   InpSignalID       = "P6";          // Signal ID (P6, P7, P8, etc.)
input int      InpMagicNumber    = 46006;          // Magic number (46000 + signal number)
input double   InpNotionalEUR    = 1000.0;         // Target notional per trade in EUR
input double   InpRiskPct        = 1.5;            // Risk per trade (%)
input double   InpSLMultiplier   = 1.5;            // SL = ATR * this multiplier
input double   InpTPMultiplier   = 2.0;            // TP = ATR * this multiplier
input string   InpExitMethod     = "simple";       // Exit method: simple or triple_barrier
input int      InpTimeoutBars    = 120;            // Triple-barrier timeout in bars
input double   InpEntryThreshold = 0.60;           // Minimum confidence to enter (ET)

//--- EA instance
CMLSignalBase trader;

//+------------------------------------------------------------------+
int OnInit()
{
   if(!trader.Initialize(InpMagicNumber, InpSignalID, InpNotionalEUR,
                         InpRiskPct, InpSLMultiplier, InpTPMultiplier,
                         InpExitMethod, InpTimeoutBars, InpEntryThreshold))
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
