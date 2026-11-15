# Server autostart inventory (ExpServer 10.10.10.100)

Policy (board directive, 2026-11-15, UGT-12): every MT5 terminal and every
related server/application on this machine MUST have an autostart entry, and
any future app added to this stack gets one at deploy time. The server gets
rebooted occasionally; nothing trading-related may depend on a manual start.

Live copy of this inventory: `C:\workspace\startup\README.md`.

## Inventory

| What | Mechanism | Detail |
|---|---|---|
| Alpari trades terminal (acct 52920535, SignalBridge/SignalReplay EAs) | Startup folder lnk | `...\Start Menu\Programs\Startup\MetaTrader 5.lnk` -> `C:\Program Files\MT5\terminal64.exe` (no args). Starts first at logon; owns MT5 MCP port 127.0.0.1:22346. |
| Pepperstone NewSetup terminal (acct 61636260, portable) | Startup folder lnk | `...\Start Menu\Programs\Startup\MetaTrader 5 Pepperstone.lnk` -> `wscript.exe C:\workspace\startup\start_mt5_pepperstone.vbs` (60 s delay, then `terminal64.exe /portable`). Delay guarantees Alpari wins the MCP port race after reboot. |
| algo_state_server :8001 | Boot scheduled task | `USO417_AlgoStateServer`: `C:\Python314\python.exe C:\workspace\fx_ml\algo_state_server.py --host 0.0.0.0 --port 8001 --config C:\workspace\fx_ml\pt_config_expserver.json` |
| mt5_api_server :8000 | Boot scheduled task | `USO417_MT5ApiServer`: `...mt5_api_server.py --host 0.0.0.0 --port 8000` (self-reports degraded in session 0 — by design) |
| monitoring_console :8002 | Boot scheduled task | `USO417_MonitoringConsole`: `...monitoring_console.py --host 0.0.0.0 --port 8002 --config ...pt_config_expserver.json` |
| paper_trader_v3 | Time scheduled task | `USO366_ForwardTest` (daily): `python C:\workspace\fx_ml\paper_trader_v3.py --config C:\workspace\fx_ml\pt_config_expserver.json` |
| GDELT pipelines | Time scheduled tasks | `GDELT_Pipeline_USO385` (run_gdelt.bat), `GDELTResume` (run_gdelt_resume.bat) — non-trading, unchanged |

## Rules

- New terminal/future app: add its entry to the user Startup folder (or a
  boot scheduled task for services), and add a row to this inventory in the
  same change.
- MT5 terminals must start in the interactive (RDP) session, never from
  session-0 services — session 0 has no MT5 IPC.
- Only ONE terminal may own python-API/MCP port 22346: always the Alpari
  trades terminal. Any new terminal launcher must delay behind it (see the vbs
  above).
- Never `taskkill /IM terminal64.exe` — it kills BOTH terminals. Target by
  install path or PID.
