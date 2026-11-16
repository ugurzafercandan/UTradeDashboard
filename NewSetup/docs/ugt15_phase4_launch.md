# UGT-15 Phase 4 launch record — 4-week paper-trading rollout (SCI Quant, 2026-11-16)

Run: 9a808eb0 (SCI Quant). This run is company-scoped (no task checkout
context); issue-tracker comment/status writes are 403-blocked
(`cross_issue_influence_run_context_required`), so this file is the record
of launch + tracker dispositions, per the established convention from
UGT-19/23/27.

## Authority to launch

- [UGT-27] final Phase-3 verdict (CTO, 2026-11-16 12:45Z): **ALL Phase-3
  gates PASS** with the tuned candidate on the untouched holdout
  (2025-01-01..2026-11-13): 667 trades, win 78.6%, PF 3.57, Sharpe 1.22,
  maxDD 0.25%; walk-forward WFER 0.749 (gate PASS); corrected holdout A/B
  (ece1dc0 fold-warmup fix) -> **adopt_candidate** (mean_diff +0.522 Sharpe,
  paired t=2.83, p=0.0046; tuned > frozen baseline on every signal-bearing
  fold). Verdict explicitly recommends proceeding to the Phase-4 paper
  rollout (paper only, no live deployment).
- CEO decision record (`docs/ceo_decision_2026-11-16.md`): "When UGT-27
  verdict lands PASS: unblock UGT-15 and launch the Phase-4 paper rollout."
- Per-window Sharpe convention resolved (daily-aggregated; `methods.md`).

## Deployed (this run)

1. **MT5 attach fix** (`data/price_provider.py`): `MT5PriceProvider` now
   attaches by explicit configured path (`settings.yaml` `mt5` section)
   instead of bare `mt5.initialize()`, which would attach to whichever
   terminal owns port 22346 — per the autostart policy that is the Alpari
   trades terminal (verified live: PID 12280 owns 22346; Pepperstone
   terminal PID 7796 does not). Added the account guard (refuse login !=
   61636260, mirror of `execution/mt5_bridge.py`), playbook->broker symbol
   mapping via `config/broker_map.yaml`, and `symbol_select()` before
   `copy_rates`. Tests: `TestMT5Provider` (guard + mapping).
2. **Paper book persistence** (`execution/paper_broker.py`,
   `main.py`, `settings.yaml`): `PaperBroker` is in-memory by design; daily
   `--once` cycles would otherwise restart the 4-week book from the starting
   balance every day. `save_state()` (atomic tmp+replace) +
   `_load_state()` (tolerant of missing/corrupt file) persist
   balance/open/closed/last prices to `data/paper_state.json` (gitignored);
   `main.py` saves at the end of every cycle. Tests: round-trip across
   processes + corrupt-file tolerance.
   - Full suite after both changes: **142 passed** (C:/Python314).
3. **Daily scheduled task** `UGT15_NewSetupPaperDaily` (Task Scheduler,
   daily 15:45 server-local, Run As Administrator, Logon Mode: Interactive
   only — same pattern as `USO366_ForwardTest`, required for MT5 python API
   IPC): runs `scripts/run_paper_daily.bat` -> `C:/Python314/python.exe
   main.py --once`, appending to `logs/paper_daily.log`. Inventory rows
   added to `C:/workspace/startup/README.md` AND repo
   `docs/server_autostart.md` in the same change (board rule UGT-12).

## Launch verification (real execution output)

- Live attach probe: login **61636260** (correct Pepperstone NewSetup
  terminal) in 0.3 s; broker-mapped D1 bars: COPPER->Copper 250,
  XTIUSD->SpotCrude 250, XAUUSD 250, SOXX.US 150 (equity depth from
  2020-06), WHEAT->Wheat 250.
- Hand-run of the exact task action (`run_paper_daily.bat`), 2026-11-16
  13:20Z: Layer 1: 12 raw signals -> Layer 2: 5 confirmed -> Layer 3: 5
  sized -> 5 paper fills -> daily report rendered -> funnel rows recorded
  -> `paper book persisted to data/paper_state.json`, exit 0.
- First scheduled run: today 15:45 server-local (task "Next Run Time:
  11/16/2026 3:45:00 PM", Status: Ready).

## Day-1 observations for the 4-week window (review items, not blockers)

- GDELT 2.0 API returned HTTP 429 on every query in both cycles today;
  the scanner fell back to offline fixtures. Event triggers fired, but event
  *freshness* is degraded while rate-limited — watch whether the daily
  window keeps getting fixture events (they are stale/deterministic).
- Three BUY fills on USDCNH from three distinct inefficiencies (#2/#3/#4)
  at the same price: layer-3 caps per-inefficiency (max 1) but does not
  dedupe per-instrument across inefficiencies, and sector exposure was not
  binding. Question for the week-1 quality review: should same-instrument
  entries aggregate under `max_sector_exposure_pct`?
- LIN.US paper-filled from an EVENT trigger although LIN.US is not offered
  on this terminal (broker_map "not offered" list): paper entry priced from
  the scanner path. Fine for paper bookkeeping, but such signals must never
  reach a live gate.

## Tracker dispositions (for the next issue-scoped heartbeat / board user)

This run could not write these (403 company-scope). All decided, evidence
in-repo:

- **UGT-25** (coordination note): close **done**. Read + executed; division
  of labor honored (my item-2 work is a31d86b; CTO confirmed closure at
  12:46Z).
- **UGT-20** (rework RESUME 2): close **done** (superseded by UGT-19/23/27;
  rework accepted per CEO decision 034ea46). Blocker UGT-22 is cancelled —
  clear the `blockedBy` edge.
- **UGT-21** (rework RESUME 3, backlog): close **done** (superseded; never
  needed).
- **UGT-26** (probe, backlog): **cancelled** per CEO decision ("empty probe
  issue created accidentally").
- **UGT-15** (this rollout): unblock (gate condition met per UGT-27
  verdict) and set **in_progress** — Phase 4 is deployed and launched per
  this record. The 4-week window ends ~2026-12-14; the go/no-go for Phase-5A
  ($5K live) stays reserved to CEO/board. No live deployment is recommended
  or enabled by this launch.
