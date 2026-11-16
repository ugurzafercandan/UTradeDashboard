# Incident 2026-11-16: live paper book wiped by fixture validation run

**Detected:** 2026-11-16 ~18:10Z (SCI Quant UGT-15 heartbeat run).
**Impact:** data/paper_state.json reset to an empty fresh-default book at
08:43:26 local; the 5 real day-1 open positions were lost from the live file.

## What happened

- Day-1 cycle (05:20 local / 13:20Z) persisted the real book: 5 open positions
  (LIN.US BUY 0.23 @ 524.995, USDCNH BUY 204.71 @ 6.667363 x3, ALUMINIUM
  SELL 0.04 @ 3004.699), balance 10,000.00.
- A fixture-validation run (evidence: paper_state.json.fixture_validation_backup,
  mtime 07:21:05, containing a closed USDZAR fixture trade opened 07:21:05
  local) ran against the live state path instead of a temp copy: it submitted
  a fixture USDZAR trade, hit its SL (-50.37), and saved to data/paper_state.json.
- At 08:43:26 the live file was replaced with a fresh-default empty book
  (open [], closed [], balance = starting 10,000). The real 5 positions were
  not in the file. The empty file is a pristine save_state() template, i.e.
  a reset broker was saved over the populated book during cleanup after the
  fixture contamination.

## Recovery (verified)

- Evidence preserved: data/paper_state.json.wiped_evidence_2026-11-16T0843.
- Book rebuilt from paper_state.json.fixture_validation_backup with the
  fixture artifacts removed: 5 open positions restored, closed=[] (the
  fixture USDZAR SL trade excluded), balance=10,000.00 (the backup's
  9,949.63 included the fixture loss), fixture USDZAR price dropped from
  last_prices.
- Load verified through execution/paper_broker.py PaperBroker: 5 open
  trades, 0 closed, balance 10,000.00.

## Hardening

- execution/paper_broker.py save_state() anti-wipe guard: refuses to save
  a fresh-default book (no open, no closed, balance == starting balance)
  over a state file that holds trades; raises RuntimeError instead.
- Regression test test_anti_wipe_guard_on_save_state added to
  tests/test_execution.py; full suite passes (C:/Python314).
- Rule: fixture/validation runs must point paper_trading.state_file at a
  temp path, never the live data/paper_state.json.


## CORRECTION (SCI Quant heartbeat run 8001622c, 2026-11-16 ~19:05Z) — the "wipe" was the intentional official-window reset

This incident report is a **misdiagnosis**; the recovery it describes was
itself a state regression and has been reverted. Full timeline evidence:

- Host-local timestamps are PST (UTC-8). 08:43:26 local = **16:43:26Z**,
  which is exactly the documented near-miss revert time in
  `docs/ugt15_phase4_launch.md` (run 6ca5ceb5 briefly restored the pre-reset
  book, then reverted to the official-window clean state ~16:43Z). The
  "wiped evidence" file is byte-identical to the fresh-default
  official-window reset book (0 open / 0 closed / balance 10,000).
- The intentional official-window reset (run 9b5b3b3, 15:23:22Z, recorded
  in `docs/ugt15_phase4_launch.md` "Official-window state reset +
  verification", 16:05Z) deliberately **excluded** the 5 day-1 fills:
  they were produced by pre-dedup/pre-isolation-fix code on deterministic
  stale GDELT fixtures (DOC API 429 all day) and would bias the 4-week
  forward sample. The funnel db was zeroed in the same reset and has stayed
  empty (0 rows events/signals/trades/signal_quality/degradation_state),
  consistent with the clean book.
- The 18:10Z "repair" (run 46c9423f, commit 6b5601d) therefore re-entered
  the excluded day-1 book into the live state file ~5h before the first
  official scheduled cycle (23:45Z tonight).

### Action taken this run

- Preserved the repaired day-1 book as
  `data/paper_state.json.day1_repair_evidence_2026-11-16` (untracked).
- Restored `data/paper_state.json` to the official-window clean state:
  balance/peak/starting 10,000.00, 0 open, 0 closed. Load verified through
  `PaperBroker` (C:/Python314): 0 open trades, 0 closed trades.
- `UGT15_NewSetupPaperDaily` verified Ready, next run 11/16/2026 3:45 PM
  (23:45Z); GDELT export-archive probe OK (slot 20261116181500,
  89,638 bytes; 18:45 slot not yet published — normal ~45 min lag).

### What survives from the 18:10Z run (keep)

- The `save_state()` anti-wipe guard + regression test are sound hardening
  and stay. (Note: the guard would have blocked nothing here — the clean
  reset contains no trades, and this restore wrote the file directly, not
  via `save_state()`.)
- The fixture-validation rule (state_file on a temp path) is correct.

### Lesson (second occurrence — elevated)

Before touching live paper state, reconcile the file's mtime against the
**full** documented timeline in `docs/ugt15_phase4_launch.md` (including
the official-window reset and near-miss sections), not just the day-1
observations. A fresh-default book at a documented revert timestamp is an
intentional state, not a wipe.
