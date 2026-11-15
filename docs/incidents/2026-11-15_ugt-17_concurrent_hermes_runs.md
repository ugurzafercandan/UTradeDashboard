# Incident 2026-11-15: UGT-17 runs failed - concurrent Hermes chats on shared state.db

**Filed by:** GenelMudur (CEO agent), heartbeat run 480ca680
**Impact:** UGT-17 (NewSetup structural rework) lost its execution path - 3 consecutive `adapter_failed` runs, retry budget exhausted, issue moved to `blocked` with a board-owned recovery action (49d0a08f).
**Status: RESOLVED** - runtime repaired; work resumed under UGT-19 (assigned to SCI Quant).

## Symptoms

- Runs `432f1549` (20:56:30Z), `01428c66` (21:00:29Z), `b07227b5` (21:01:29Z) on UGT-17 all failed with `adapter_failed`, "Hermes exited with code 1".
- Hermes output in run logs: "No reply: Hermes couldn't save this conversation, so it stopped rather than lose your messages. Possible causes: the drive is out of room, or another Hermes process is holding the database."

## Root cause

All Paperclip agents on this host share one Hermes home (`C:/Users/Administrator/AppData/Local/hermes`, single `state.db`, WAL mode) and one gateway process. The engine's per-agent `runtimeConfig.heartbeat.maxConcurrentRuns` was 20, so it started an issue-wake run **while the same agent's heartbeat run was still live**:

- heartbeat run `e95286bd` 20:53:58-20:59:07Z - **succeeded** (held state.db writes)
- issue-wake run `432f1549` 20:56:30-20:59:33Z - **crashed** ("couldn't save this conversation", state.db write contention)
- Both scheduled retries (15s and 13s) then hit the same save failure and exited 1.

Not a disk or corruption problem: 433 GiB free; `hermes doctor` reports state.db healthy (67 sessions, WAL mode, FTS intact).

## Fix applied (CEO, verified via API echo)

`runtimeConfig.heartbeat.maxConcurrentRuns`: **20 -> 1** on all 5 agents (GenelMudur, CTO, CTO Advisor, CDO, SCI Quant). The engine now serializes each agent's runs, so an issue wake queues behind a live heartbeat instead of colliding on state.db.

Residual risk: two *different* agents' runs can still overlap (cross-agent concurrency is not serialized). Same-agent collision - the observed failure mode - is eliminated. If a cross-agent save collision ever appears, the same treatment (engine-level serialization or per-agent Hermes homes) is the escalation path.

## Recovery

- UGT-17 stayed `blocked` (board-escalation recovery action; agent API cannot retry another agent's runs - by design).
- CEO filed **UGT-19** (child of UGT-5, assigned to SCI Quant, high priority) carrying the full UGT-17 spec, so the structural rework continues without waiting for board action. SCI Quant's assignment run 64a756cd started 2026-11-15T21:26:07Z.
- Board cleanup (optional): resolve recovery action 49d0a08f on UGT-17 (restored/reassigned, or closed as superseded by UGT-19).

## Lessons

- On a shared Hermes home, `maxConcurrentRuns > 1` per agent is unsafe with the hermes_local adapter. Default new agents to 1.
- "adapter_failed / Hermes exited code 1" within seconds of run start => check the run log (`GET /api/heartbeat-runs/{runId}/log`) for the save-failure message before assuming a task problem.
