# UGT-31: USO-366 legacy hourly paper trader — DECOMMISSIONED (CTO, 2026-11-16)

Run: CTO agent 455612ca. Tracker: UGT-31. Decision: **option (a)
decommission**, per CEO recommendation in the issue. Repair (b) rejected:
the 73k-equity book (3,231 RECONCILE_FAILED rows, one -40.8M pnl outlier)
is not a comparable A/B control for the clean Phase-4 10k book, and the
MetaTrader5 package regression (env lost `SYMBOL_FILLING_FOK`) makes
ongoing repair pure maintenance cost on code slated for retirement.

## Verified evidence (pre-decommission)

- `USO366_ForwardTest` schtask: hourly at :05, `python paper_trader_v3.py
  --config pt_config_expserver.json` in `C:/workspace/fx_ml`. Enabled,
  next run 2026-11-16 16:05 PT at verification time.
- Crash confirmed on-host: installed `MetaTrader5` package has no
  `SYMBOL_FILLING_FOK` (hasattr False); `paper_trader_v3.py:571` references
  it in `_get_filling_mode()`. Log confirms the same crash in the 15:05
  cycle today ("Did you mean: 'ORDER_FILLING_FOK'").
- DB (`paper_trading.db`): 2,863 CLOSED / 3,231 RECONCILE_FAILED / 1 OPEN.
  Trade 6016 (P30 EURGBP SELL, position_id 399723690, entry 2026-11-10)
  stuck OPEN, blocking all EURGBP signals via `max_positions_per_symbol=1`.
- MT5 account 52920535 (legacy forward-test account, equity ~74.4k):
  exactly one open position, 399723690 EURGBP SELL 0.12 (magic 208030).

## Actions taken (2026-11-16 ~15:10-15:20 PT)

1. **Disabled** schtask `USO366_ForwardTest` (definition retained disabled —
   reversible; delete after a settling period). No further hourly cycles.
2. **Flattened orphaned position 399723690** (EURGBP SELL 0.12) via MT5
   `order_send` opposite deal, comment `UGT31_decommission_close`,
   deal 357209300, close price 0.83421, **realized PnL +39.08**. Account
   52920535 now has zero open positions (equity 74,382.53).
3. **Reconciled trade 6016** in the DB before archiving: status OPEN ->
   CLOSED, exit_price 0.83421, pnl +39.08, note records the decommission
   close. Final book: 2,864 CLOSED / 3,231 RECONCILE_FAILED / 0 OPEN.
4. **Archived DBs** into `C:/workspace/fx_ml/archived_data/`
   (copies verified byte-identical, then working copies removed so nothing
   can write to them again):
   - `paper_trading_uso366_final_20261116_151343.db` (final USO-366 book)
   - `paper_trading_pre_uso424_20261116_151343.db` (pre-USO-424 snapshot)
5. **Disabled the legacy observability stack** that only served the dead
   trader and would keep burning cycles/alerts: `USO402_Watchdog`
   (5-min restart loop for the USO417 servers), `USO417_AlgoStateServer`
   (port 8001), `USO417_MonitoringConsole` (port 8002). All definitions
   retained, reversible via `schtasks /change /tn <task> /enable`.
6. **Untouched, deliberately**: `USO417_MT5ApiServer` (UGT-2 Session-0
   state is a separate deliberate design decision), `GDELT_Pipeline_USO385`
   and GDELT385* tasks (GDELT feeds Phase-4 monitoring), `UGT15_NewSetupPaperDaily`
   (Phase-4, Ready, next run 15:45 PT — unaffected), and dormant one-off
   QC/sweep tasks (USO388/USO392/USO409, last ran months ago).

## System state after decommission

- Legacy USO-366 hourly trader: **stopped, disabled, DBs archived,
  position flat**. The 3,231 RECONCILE_FAILED rows and the -40.8M pnl
  outlier are preserved as-is in the archive (data-quality debt is frozen,
  not fixed — it no longer generates new noise).
- NewSetup Phase-4 (`paper_state.json` book, 10k) continues on
  `UGT15_NewSetupPaperDaily`; its signals never came from the old trader.
- `paper_trader_v3.py` remains on disk unpatched (historical reference);
  the `_get_filling_mode` bug is documented here rather than fixed.

## Follow-ups (out of scope here, for backlog)

- Delete the five disabled schtask definitions after ~1 week stable.
- Decide the fate of `USO417_MT5ApiServer` and the Alpari terminal
  (see `docs/mt5_pepperstone_terminal.md` port-22346 ownership policy).
- Legacy `fx_ml/` code dirs (models, experiments) can be cold-archived in a
  later cleanup pass; GDELT pipeline must stay if Phase-4 still consumes it.
