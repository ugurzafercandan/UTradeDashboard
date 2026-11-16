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
