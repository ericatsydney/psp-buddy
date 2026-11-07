# Debugger freeze — implementation plan

Spec: [2026-11-07-debugger-freeze-design.md](../specs/2026-11-07-debugger-freeze-design.md). Approved 7 Nov.
Nothing is committed until the user asks.

Verification commands (repo root, project venv):

```
.venv/Scripts/python.exe -m pytest -q                      # unit + scenarios (live excluded)
.venv/Scripts/python.exe -m pytest -q local/move-attack-trial-20261017 local/m15-tools local/m17-tools
.venv/Scripts/python.exe -m ruff check src tests
.venv/Scripts/python.exe -m mypy src
```
Expected: all pass (baseline 4 Nov: pytest 1770 / 1 skipped, local tools + helper 233).

## Task 1 — request trace (TDD)
Files: `src/psp_buddy/debugger.py`, `tests/unit/test_debugger.py`,
`local/move-attack-trial-20261017/handoff.py` (+ its test).
1. Tests first (fail): `adapter.trace` receives one record per `_exchange` with event, ticket,
   seconds, outcome `ok`; a silent request under a short timeout gives outcome `timeout` (and still
   raises); an error reply gives `error: RuntimeError`; a trace callback that raises does not change
   the request result and increments `adapter.trace_errors`.
2. Implement in `_exchange` (`finally` block; clock = `time.monotonic_ns`).
3. Handoff: `TraceWriter(evidence_dir)` appends JSON lines to `debugger-trace.jsonl`, rotates at 5000
   lines to `debugger-trace.1.jsonl`; set `adapter.trace` right after `connect_live`. Test with tmp dir.

## Task 2 — `_act_read` outcome (TDD)
File: `src/psp_buddy/info_navigation.py`, `tests/unit/test_act_navigation.py`.
Test: a read raising `TimeoutError` logs `"outcome": "timeout"` and re-raises; other exceptions log
their type name. Implement with a broad `except BaseException` that records then re-raises.

## Task 3 — settle dialogue before a `cursor_budget` handover (TDD)
File: `src/psp_buddy/info_navigation.py`, `tests/unit/test_act_navigation.py` (turn_next tests).
Tests: with `_dialogue_pending` and an over-budget next unit, `turn_next` calls `settle_dialogue`
before writing the handover; settled -> pending cleared; not settled -> handover keeps reason
`cursor_budget` and `handover.json` has `dialogue_pending: true`.

## Task 4 — freeze probe tool
Files: `local/m17-tools/freeze_probe.py`, `local/m17-tools/test_freeze_probe.py`.
- Reuses `run.py` launch/quiet/backup helpers and the trial helper's mailbox (`act` IO operations
  exposed for probing: open the weapon list via the existing act path with `commit:false`, stopping at
  the weapon list; then `probe_cycle` = one press + one `menu_row` read).
- Freeze detection > 10 s; recovery attempts (a) wait 120 s, (b) WM_NULL via SendMessageTimeout,
  (c) second WebSocket (probe-only bypass, same PID, loopback); then cpu.status / resume.
- Offline tests: cycle bookkeeping, freeze detection, recovery ordering with fakes, report shape.

## Task 5 — protected live probe (max 2 runs)
Portable memstick backup (55 files, SHA-256) + runner backup; probe on the slot-2 checkpoint
`slot2-20261106T2255`; after: originals unchanged. Record results in `docs/progress.md`.

## Task 6 — runner recovery (TDD, from Task 5's answer)
File: `src/psp_buddy/debugger.py` (freeze timeout 10 s, recovery hook), `info_navigation.py`
(`debugger_frozen` handover, `freezes_recovered` count), tests in `test_debugger.py` and
`test_act_navigation.py`. Only the recovery the probe proved is implemented.

## Task 7 — checks, review, live run
Run all verification commands; code review of `git diff HEAD` + untracked files; fix Critical/Important;
protected live run on the user's slot 2; update `docs/progress.md`.
