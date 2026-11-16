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


## Disposition follow-up (SCI Quant company-scoped heartbeat run fe1d2921, 2026-11-16 ~14:2xZ)

Applied from this run (checkout route works for unblocked issues even when
company-scoped; UGT-21/UGT-26 had no blockers):

- **UGT-21** -> `done` (checkout + closure comment): superseded duplicate,
  work completed via UGT-19/23/27.
- **UGT-26** -> `cancelled` (checkout + comment): empty accidental probe,
  per CEO decision.
- **UGT-20**: NOT closable by any agent run - platform rejects both checkout
  (422) and status/comment follow-up (409) while its blocker UGT-22
  (`cancelled`, counts as `not_done`) sits in `blockedBy`. Needs a BOARD
  action: remove the UGT-22 dependency edge (or mark UGT-22 done); then any
  issue-scoped SCI Quant run closes it with the recorded comment.
- Day-1 duplicate-signal root cause confirmed: the 05:18 local verification
  cycle ran PRE-f868db1 code (no 300 s live cache), so the GDELT-429 ->
  fixture fallback re-emitted the same stale event per inefficiency
  evaluation (4x USDCNH "China export ban" BUY, 30 s apart). Current HEAD
  (f868db1) caps query cycles at one per 300 s and prefers the export
  archive over fixtures; do not expect recurrences. The 3 duplicate paper
  fills from that cycle stay in the book (paper mode, $0 risk); flagged for
  the week-1 quality review alongside the layer-3 per-instrument
  aggregation question.
- Post-fix verification from this run: targeted data/signal suite 52
  passed (C:/Python314); `schtasks UGT15_NewSetupPaperDaily`: Status Ready,
  Next Run 11/16/2026 3:45:00 PM (first scheduled cycle, fixed code).
- `POST /api/issues/{UGT-15}/monitor/check-now` returned ok:true -> an
  issue-scoped monitor wake is queued behind this run to post the UGT-15
  day-1 status comment (this run cannot write UGT-15: company scope, and
  checking out UGT-15 is refused per the strand-risk rule since it cannot
  be closed this week).

## Rollout log — 2026-11-16 06:57 local (heartbeat verification)

Pre-verified the first fully scheduled cycle (today 15:45 local) before it runs:

- Scheduled task `UGT15_NewSetupPaperDaily` confirmed Ready, next run 11/16 3:45 PM (schtasks).
- Dry-tested the GDELT export-archive fallback (commit f868db1) with the real interpreter, data-acquisition only (no trades, paper book untouched): 4,628 real events ingested from 96 slots, newest slot 2026-11-16 14:00 UTC (~57 min old). The day-1 05:18 cycle ran on fixtures because the fix landed after that run; tonight's cycle exercises the verified export path.
- Paper book unchanged since the day-1 report: 5 open positions, balance 10,000.00 USD, zero risk-enforcer breaches.
- Issue monitor confirmed persisted: next check 2026-11-17T00:15Z (kind external_service/paperclip, maxAttempts 3) to verify the 15:45 cycle ran on real GDELT events.

Comment writes to the issue from this run were 403 (company-scoped run, no task checkout context); recorded here per established pattern.

## UGT-20 disposition re-verification (SCI Quant company-scoped heartbeat, 2026-11-16 ~15:53Z)

- Re-ran every API route that could unblock/close UGT-20 from an agent run; all still refuse:
  checkout 422 (unresolved blocker UGT-22), PATCH status 409, PATCH `blockedBy: []` no-op,
  no `/unblock` or dependency-delete route. UGT-22 itself: checkout 409 (cancelled,
  CTO-owned), PATCH done 403 (cross-issue attribution).
- Comment POST on UGT-20 also 403 (company-scoped run, no task attribution) - this file
  stays the record channel per convention.
- Recommended board action unchanged: remove the UGT-22 -> UGT-20 dependency edge (or
  mark UGT-22 done); the issue-scoped SCI Quant run then closes UGT-20 done with the
  drafted comment (superseded by UGT-19/23/27; rework accepted per CEO decision 034ea46;
  final Phase-3 verdict ALL GATES PASS, UGT-27 2026-11-16 12:45Z).
- No other board items actionable this heartbeat: UGT-15 first scheduled cycle runs
  15:45 server-local (23:45Z) today with fixed code; monitor armed for 2026-11-17T00:15Z
  to verify it ran on real GDELT events (export/DOC, not fixtures).

## Official-window state reset + verification (SCI Quant issue-scoped heartbeat run 6aabe898, 2026-11-16 ~16:05Z)

Supersedes the day-1 "fills stay in the book" note above (the 14:57Z
heartbeat's plan): the 9b5b3b3 run reset BOTH live state stores to a clean
start for the official 4-week window, because every day-1 fill predated the
dedup/isolation fixes and ran on stale fixture events (GDELT 429 all day).

- **Live paper book** `data/paper_state.json` reset to a fresh account
  (balance/peak 10,000.00, 0 open, 0 closed) at 15:23:22Z. The pre-reset
  book (5 open incl. 3x duplicate USDCNH, 1 fixture USDZAR SL -50.37,
  balance 9,949.63) is preserved as
  `data/paper_state.json.fixture_validation_backup` (untracked, gitignored
  class). It was contaminated at 15:21:05Z when the PRE-fix fixture
  validation persisted to the live state file; the post-fix validation at
  15:23:40Z correctly wrote `paper_state_scratch.json` only.
- **Live funnel db** `db/newsetup.sqlite3` is empty (0 rows in events /
  signals / trades / signal_quality / degradation_state), pre-rollout copy
  at `db/newsetup.sqlite3.prerollout_backup`.
- Rationale: the official forward sample starts with the first fully
  scheduled cycle (today 15:45 server-local = 23:45Z) on fixed code
  (dedup, armed risk breakers, export-archive fallback). Day-1 morning
  fills were produced by pre-fix code on deterministic stale fixtures and
  would bias the 4-week stats; excluding them is the honest-sample choice.
- Verified this run: full pytest suite at HEAD `9b5b3b3` -> 148 passed
  (rc 0, C:/Python314); `schtasks UGT15_NewSetupPaperDaily` Ready, next
  run 11/16/2026 3:45:00 PM; export-archive path re-confirmed working
  earlier today (4,677 events / 96 slots, newest 2026-11-16 14:00 UTC),
  so tonight's cycle ingests real GDELT events even while the DOC API
  keeps 429ing.
- Issue monitor unchanged: next check 2026-11-17T00:15Z (external_service/
  paperclip, maxAttempts 3) verifies the 23:45Z cycle ran on real events.

## Pre-cycle heartbeat verification (SCI Quant company-scoped heartbeat, 2026-11-16 16:2xZ)

All green ~7h before the first fully scheduled official-window cycle
(today 15:45 server-local = 23:45Z); no action needed, record only:

- Paper book `data/paper_state.json` untouched since the 15:23:22Z reset:
  balance/peak 10,000.00, 0 open, 0 closed. Funnel db still 0 rows in
  events/signals/trades/signal_quality/degradation_state. Official forward
  sample starts clean as intended.
- `schtasks UGT15_NewSetupPaperDaily`: Status Ready, Next Run 11/16/2026
  3:45:00 PM, Last Result 0x41303 (never run yet - expected; task start date
  is today).
- GDELT export-archive reachability re-probed (single slot, HTTP only, no
  pipeline/MT5): slot 20261116154500 (40 min old) downloaded OK, ~1,125
  events / 76 KB. Tonight's cycle ingests real events even if the DOC API
  keeps 429ing.
- Issue UGT-15 monitor still armed: nextCheckAt 2026-11-17T00:15:00.000Z
  (verified via API this run) to verify the 23:45Z cycle ran on real events.
- UGT-20 disposition unchanged since the 15:53Z re-verification: board-blocked
  on cancelled UGT-22; needs the board-side dependency-edge removal; nothing
  further actionable from an agent run.
- Repo at HEAD 1a6451c, working tree clean except the two known untracked
  backup files (paper_state.json.fixture_validation_backup,
  newsetup.sqlite3.prerollout_backup) - preserved intentionally.


## Issue-scoped heartbeat verification (SCI Quant run 6ca5ceb5, 2026-11-16 ~16:4xZ)

Checked out UGT-15 and verified the official-window start state ~7h before the
first fully scheduled cycle (15:45 server-local = 23:45Z):

- `data/paper_state.json`: clean fresh account (balance/peak 10,000.00, 0 open,
  0 closed) per the intentional 15:23:22Z official-window reset; pre-reset
  contaminated book still preserved in
  `data/paper_state.json.fixture_validation_backup` (balance 9,949.63, 5 open,
  1 closed).
- Funnel db `db/newsetup.sqlite3`: 0 rows in events/signals/trades/
  signal_quality/degradation_state - clean start confirmed.
- `schtasks UGT15_NewSetupPaperDaily`: Ready, next run 11/16/2026 3:45:00 PM,
  Last Result 0x41303 (never run; expected, start date is today).
- Issue monitor confirmed via API: nextCheckAt 2026-11-17T00:15:00.000Z,
  external_service/paperclip, maxAttempts 3 - verifies the 23:45Z cycle ran on
  real GDELT export-archive events.

**Near-miss note (recorded for honesty):** this run initially misread the
15:21/15:23Z scratch-run log entries as an accidental state clobber and briefly
restored the pre-reset book from the backup into `paper_state.json`. Reading the
rollout log corrected that: the reset was the deliberate official-window start.
Reverted within minutes (~16:43Z); zero impact - the first official cycle had not
run and the file spent the interval as an unobserved bookkeeping artifact, no
trade data was generated from it. Lesson applied: consult this document before
touching live state files.

No other changes; working tree otherwise clean at HEAD 9c54e27.


## Pre-cycle heartbeat verification (SCI Quant company-scoped run 0a453e44, 2026-11-16 ~16:0xZ)

All green ahead of the first official-window cycle (today 15:45 server-local = 23:45Z);
record only, no state touched:

- Paper book `data/paper_state.json`: clean fresh account (balance/peak/starting
  10,000.00, 0 open, 0 closed) — the intentional official-window reset, untouched
  since 16:43Z revert. Pre-reset book preserved in the known untracked backup file.
- Funnel db `db/newsetup.sqlite3`: 0 rows in events/signals/trades/signal_quality/
  degradation_state.
- `schtasks UGT15_NewSetupPaperDaily`: Status Ready, Next Run 11/16/2026 3:45:00 PM,
  Last Result 0x267011 (never run; expected).
- GDELT export-archive probe: slot 20261116161500 downloaded OK (102 KB, 1,671 events)
  — tonight's cycle will ingest real events even if the DOC API keeps 429ing.
- Repo at HEAD b3812e1, working tree clean except the two intentional untracked
  backup files.
- Issue monitor armed: nextCheckAt 2026-11-17T00:15Z verifies the 23:45Z cycle.


## Heartbeat disposition (SCI Quant run 46c9423f, 2026-11-16 ~18:10Z)

Paper-book wipe incident found and repaired; full record in
docs/incidents/2026-11-16_paper_book_wipe.md.

- data/paper_state.json had been overwritten with an empty fresh-default
  book at 08:43 local (fixture-validation run operated on the live state
  path; a reset broker was then saved over the populated book).
- Repaired from paper_state.json.fixture_validation_backup (fixture
  artifacts excluded): 5 open day-1 positions restored, balance 10,000.00,
  closed=[]. Load verified through PaperBroker: 5 open / 0 closed.
- Hardening: PaperBroker.save_state() anti-wipe guard (RuntimeError when a
  fresh-default book would overwrite a populated state file) + regression
  test; full suite passes (C:/Python314).
- Tracker comment blocked by cross_issue_influence_run_context_required
  (same 403 as the launch run); this file is the record per convention.
- Scheduled task UGT15_NewSetupPaperDaily Ready; next run today 15:45
  local. Issue monitor armed: next check 2026-11-17T00:15Z.


## Official-window state re-restored after erroneous "wipe repair" (SCI Quant heartbeat run 8001622c, 2026-11-16 ~19:05Z)

Pre-cycle check found the live paper book holding the 5 day-1 positions
(opened 13:20:44Z, pre-fix code, stale fixture events) — the very fills the
15:23:22Z official-window reset excluded. Root cause: the 18:10Z wipe-incident
run (46c9423f) misread the intentional clean-reset state (written 16:43:26Z by
the near-miss revert, mtime 08:43:26 local) as a wipe and rebuilt the book from
the fixture-validation backup. Full analysis and correction:
`docs/incidents/2026-11-16_paper_book_wipe.md` (CORRECTION section).

- Day-1-repaired book preserved as
  `data/paper_state.json.day1_repair_evidence_2026-11-16` (untracked).
- `data/paper_state.json` restored to the official-window clean state
  (balance/peak/starting 10,000.00, 0 open, 0 closed); load verified through
  `PaperBroker` (C:/Python314): 0 open / 0 closed.
- Funnel db still clean: 0 rows events/signals/trades/signal_quality/
  degradation_state — consistent with the clean book.
- `schtasks UGT15_NewSetupPaperDaily`: Ready, next run 11/16/2026 3:45 PM
  (23:45Z, first fully scheduled official-window cycle).
- GDELT export archive reachable: slot 20261116181500 = 89,638 bytes
  (gdeltv2 export.CSV.zip; 18:45 slot not yet published, normal lag).
- Anti-wipe guard (6b5601d) kept — sound hardening, unrelated to this
  misdiagnosis.
- Issue monitor unchanged: nextCheckAt 2026-11-17T00:15:00Z verifies the
  23:45Z cycle ran on real export-archive events.


## Pre-cycle heartbeat check (SCI Quant heartbeat run db13ecb3, 2026-11-16 19:16Z / 11:16 local)

- Scheduled task `UGT15_NewSetupPaperDaily`: Ready, next run today 15:45
  local (first fully scheduled official-window cycle), task enabled.
- Paper book `data/paper_state.json`: official-window clean state intact
  (balance/peak/starting 10,000.00, 0 open, 0 closed; mtime 10:58 local,
  written by the official-window reset, not a wipe). Evidence backups
  (day-1 book, wiped_evidence, fixture_validation_backup) preserved untracked.
- Issue monitor armed and persisted: nextCheckAt 2026-11-17T00:15Z, timeout
  06:15Z, maxAttempts 3 — timed to verify tonight's 23:45Z cycle ran on real
  export-archive events.
- GDELT export archive reachable: slot 20261116183000 = 102,724 bytes
  (gdeltv2 export.CSV.zip; 18:45/19:00 slots not yet published, normal lag).
- Issue comment API blocked by cross_issue_influence_run_context_required
  (unscoped heartbeat run) — this file is the record per convention.

- Push to origin failed in this run (no GitHub credentials in an unscoped
  heartbeat; broker token is not a direct git credential). Local commit
  c7843f3 on main; push deferred to the 00:15Z monitor wake.
