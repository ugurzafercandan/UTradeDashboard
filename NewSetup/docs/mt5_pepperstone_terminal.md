# Pepperstone MT5 Terminal (NewSetup execution terminal)

Status: LIVE and verified 2026-11-15 (UGT-10, commit 85a3bed).

## Terminal

- Install: `C:\Program Files\MT5-Pepperstone\terminal64.exe`
- Mode: `/portable` (own data folder inside the install dir; fully isolated
  from the fx_ml/Alpari terminal at `C:\Program Files\MT5`)
- Start: `terminal64.exe /portable`

## Account (Pepperstone Razor DEMO)

- Login: 61636260
- Password: ocf4Pb;vxu
- Server: Pepperstone-Demo
- Currency USD, leverage 1:500, starting balance 50,000
- Owner: Ugur Zafer Candan

## NewSetup integration

- `config/settings.yaml` `mt5` section points the bridge at this terminal
  (path, portable, login, server). Password is injected via the
  `PEPPERSTONE_MT5_PASSWORD` environment variable — never stored in the repo.
- `execution/mt5_bridge.py` enforces an account guard: connection is refused
  and orders blocked if the terminal is logged into any account other than
  61636260. This matters because only ONE terminal per machine can own the
  python API socket (127.0.0.1:22346).

## Symbol naming (verified live)

- Commodities: `XTIUSD -> SpotCrude`, `COPPER -> Copper`, `COCOA -> Cocoa`,
  `WHEAT -> Wheat`, `ALUMINIUM -> Aluminium` (mixed-case contract names).
- US stocks/ETFs: identity `.US` tickers (AAPL.US, MSFT.US, COPX.US, QQQ.US,
  SOXX.US, URA.US ...).
- Not offered: ABB, BHP, CCJ, CLF, SCCO, REMX, TAN, TE, DAR, FRO, LIN, MATX,
  MOWI, MP, NTR, STNG, VALE, ZIM.

## Operational constraint

Only one MT5 terminal can own the python API port per machine. The Pepperstone
terminal currently owns it. Do not restart fx_ml paper trading (Alpari
terminal) until the ownership policy is decided (options: dedicate this
machine to NewSetup, or move one terminal to a separate machine/VM).
