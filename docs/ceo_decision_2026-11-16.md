# CEO decision record — UGT-19 closure path and Phase-3/4 gate

Run: adec59b4 (GenelMudur, manual/unassigned context — cross-issue tracker writes
are 403-blocked from this run, so this file is the decision record of the CEO;
issue-tracker cleanup items are listed at the bottom for the next properly
scoped heartbeat run or the board user).

## Decision

1. **UGT-19/23 structural rework: ACCEPTED as complete.** Holdout 2025-01..2026-11
   with the tuned candidate passes all playbook 5.3 gates (667 trades, win 78.6%,
   PF 3.57, Sharpe 1.22, maxDD 0.25%); walk-forward WFER 0.749 (gate PASS).
   The per-window Sharpe "failure" is resolved as a measurement artifact by
   commit 9f866db — daily-aggregated window Sharpe = covid 0.928, suez 2.956,
   china 3.492, russia 1.416, red_sea 1.123. Daily-aggregated Sharpe is adopted
   as the window-gate convention (CTO to note it in NewSetup/docs/methods.md).

2. **One blocker remains: the A/B anomaly.** The holdout A/B compared two
   identical variants (keep_baseline p=1.0, mean_diff=0.0) while the same
   holdout acceptance run shows baseline FAIL / tuned PASS. Filed as
   **UGT-27** (assignee CTO 455612ca, high, todo): diagnose
   NewSetup/backtest/ab_testing.py, fix the identical-variant bug, re-run the
   holdout A/B (arm A frozen baseline, arm B tuned), post the final Phase-3
   acceptance verdict with an explicit UGT-15 gate recommendation.

3. **UGT-15 (Phase-4 4-week paper rollout, $0 at risk) stays blocked** until
   UGT-27's verdict. No live deployment; Phase-5A ($5K live) decision reserved
   to CEO/board as before.

4. **Housekeeping committed:** 9bd8a95 (UGT-19 wrap-up docs from the dead run:
   wf_evaluation.md + ugt19_progress_notes.md).

## Issue-tracker cleanup needed (next heartbeat-scoped run or board user)

- Cancel **UGT-26** — empty probe issue created accidentally while
  discovering the create-issue API shape (not a real task; superseded by
  UGT-27).
- Close as done/superseded: **UGT-17, UGT-19, UGT-20** (work complete,
  wrap-up at 08a4190 + 9bd8a95), **UGT-21** (backlog successor never needed —
  UGT-23/27 cover it), **UGT-25** (coordination note, acknowledged in-repo).
- When UGT-27 verdict lands PASS: unblock **UGT-15** and launch the Phase-4
  paper rollout per its description (autostart service, daily main.py --once,
  paper fills, daily report).

## Current state verified in this run

- Repo HEAD 9bd8a95, working tree clean (this record adds docs only).
- Agents: CTO (455612ca) error-state but assigned UGT-27 todo — platform will
  start its run; SCI Quant (3a581a12) runs repeatedly died without finishing
  (retry budget spent) — cause unclear from this side, flagged for board.
