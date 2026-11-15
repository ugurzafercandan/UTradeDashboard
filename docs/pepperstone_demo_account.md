# Pepperstone Razor Demo Account — NewSetup Terminal (UGT-6)

Dedicated MT5 terminal for the NewSetup environment. Verified live and authorized on
2026-11-15 (see UGT-6 report). All agents: use these credentials for the NewSetup
Pepperstone terminal only.

## Login details (demo account — shared company-wide by board direction)

| Field | Value |
|---|---|
| Name | Ugur Zafer Candan |
| Account Number | 61636260 |
| Password | ocf4Pb;vxu |
| Currency | USD |
| Leverage | 500:1 |
| Server (MT5 URL) | Pepperstone-Demo |
| Mode | Demo, hedging |

## Terminal installation

- Path: `C:\Program Files\MT5-Pepperstone` (portable mode, `/portable`)
- Config: `Login=61636260`, `Server=Pepperstone-Demo` in `Config\common.ini`
- Autostart at logon via `C:\workspace\startup\start_mt5_pepperstone.vbs` (60 s delay)
- Verified: "authorized on Pepperstone-Demo", trading enabled (demo, hedging),
  1729 symbols synchronized (log `logs/20261115.log`)

## Operating rules (do not break)

1. One terminal per machine owns the MT5 python API socket (22346) — that is the
   Alpari terminal (`C:\Program Files\MT5`, account 52920535, fx_ml/AlgoSignal).
   The Pepperstone terminal is attached for NewSetup runs only; never run both
   with the python API at the same time.
2. `NewSetup/execution/mt5_bridge.py` has an account guard — automated trading only
   executes against account 61636260 when targeting the Pepperstone terminal.
3. Never `taskkill terminal64.exe` by image name — it kills BOTH terminals. Kill by PID.
