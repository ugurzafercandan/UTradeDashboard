# UGT-42 Deployment Report - AlgoSignal package on the Pepperstone MT5 terminal

Date: 2026-11-21
Issue: UGT-42
Source: AlgoSignal_FullPackage.zip (USO-469 deployment package, attached to the issue)

## What the package contains

- 10 news-event Expert Advisors (Algo01-10) + MLSignal_Universal (USO-465), driven
  by NewsTraderFramework.mqh and the MT5 economic calendar
- 5 v2 M5-monitored winners (P01/P43/P45/P47/P48_v2, magics 209001-209048) on top of
  NewsTraderFramework.mqh + M5MonitorFramework.mqh
- KillLosers.mq5 script (closes positions for 15 killed signals, magics 208014-208046)
- ml_signal_server python package (USO-465): 27 ML signal configs (P6-P32), file-based
  signal delivery (ml_signal_<ID>.json in MQL5\Files), tiered sizing + 40% per-currency cap
- Deployment docs: DEPLOY_INSTRUCTIONS.md, kill_signals.json (15 killed signals, -$31,274),
  ARCHITECTURE_REVIEW.md

## Applied to C:\Program Files\MT5-Pepperstone (portable terminal, data folder = install dir)

Copied into MQL5\:
- Include\NewsTraderFramework.mqh, M5MonitorFramework.mqh, MLSignalFramework.mqh
- Experts\NewsPortfolio\Algo01-10 + MLSignal_Universal
- Experts\V2\P01_v2, P43_v2, P45_v2, P47_v2, P48_v2
- Scripts\KillLosers.mq5
- Files\forex_factory_events.csv
- Files\AlgoSignal_docs\ (package deployment docs, audit copy)

## Compile results (MetaEditor64 CLI, /portable)

All 17 programs compiled with 0 errors, 0 warnings. One source fix was required:

- MLSignalFramework.mqh used FileGetDate(), which does not exist in MQL5.
  Replaced with FileOpen + FileGetInteger(FILE_MODIFY_DATE) (patch applied to the
  deployed copy and this repo copy). MLSignal_Universal then compiled clean.

## Python services attached

1. NEW - UGT42_MLSignalServer (scheduled task, logon trigger, interactive):
   C:\workspace\fx_ml\run_ml_signal_service.bat -> C:\Python314\python.exe
   C:\workspace\fx_ml\run_ml_signal_service.py (cycle 900s).
   Deploys the ml_signal_server package to C:\workspace\fx_ml\ml_signal_server and writes
   ml_signal_<ID>.json into the Pepperstone MQL5\Files for MLSignal_Universal.
   Verified live: attaches to the running Pepperstone terminal, fetches H1 bars for all
   27 symbols, writes 27 signal files (currently HOLD/0.0 - no models present).
   Missing dependency backtesting.indicators was NOT shipped in the zip; a minimal
   standard-TA implementation was provided at C:\workspace\fx_ml\backtesting\indicators.py
   (RSI/MACD/BB/ATR). Validate formulas against the trainer's originals when model
   files arrive. Models go into C:\workspace\fx_ml\models\ml_signals (currently 0/27).
   Also installed: pip loguru.

2. USO417_MT5ApiServer (existing, boot trigger): C:\workspace\fx_ml\mt5_api_config.json
   created with mt5_path = C:\Program Files\MT5-Pepperstone\terminal64.exe; task restarted,
   port 8000 healthy (degraded mode expected in session 0 - known limitation).

3. NewSetup performance tracker (UGT-15, UGT15_NewSetupPaperDaily): already points at the
   Pepperstone terminal (NewSetup/config/settings.yaml mt5.terminal_path) - no change needed.

## Boot persistence

- C:\workspace\fx_ml\uso382_startup.ps1 (runs from the ProgramData Startup folder at every
  interactive logon) updated: now starts BOTH terminals individually by path
  (old MT5, and MT5-Pepperstone with /portable) and starts UGT42_MLSignalServer.
  Verified end-to-end: both terminals detected running, service tasks started,
  paper_trader health check PASSED.
- FIX: the ps1 contained UTF-8 em dashes without a BOM, so PowerShell 5.1 misparsed it
  (broken since ~Sept; it silently failed at the Nov-15 logon - no startup.log entries since
  2026-09-27). Rewritten with a UTF-8 BOM; now parses clean.
- NOTE: after a reboot, everything starts at the first interactive logon (RDP). The server
  has no Windows auto-logon configured. If unattended boot trading is required, auto-logon
  must be enabled (stores credentials in the registry - needs explicit approval).
- Known conflict: the startup script also auto-starts USO417_AlgoStateServer (8001) and
  USO417_MonitoringConsole (8002), which are currently Disabled. Restored their disabled
  state after the verification run. Decide: re-enable or remove from the startup script.

## Not done (needs a human decision - live trading)

- Attaching the EAs to live charts on the Pepperstone account (per DEPLOY_INSTRUCTIONS
  Phase 2: 5 v2 EAs on M5 charts, magics 209xxx) and enabling algo trading.
- KillLosers execution (Phase 1): the new Pepperstone terminal has no 208xxx positions
  to kill; the script is compiled and ready if needed.
- MT5 starts only after a user logs on (see auto-logon note above).

## Files in this directory

- AlgoSignal_FullPackage.zip: original attachment (unmodified)
- mt5_eas/, ml_signal_server/, deployment/: extracted package (MLSignalFramework.mqh
  carries the FileGetDate fix)
