# M12 Live checkpoint and retries — implementation plan (25 Oct 2026, uncommitted)

Spec: [design](../specs/2026-10-25-checkpoint-retry-design.md).

Verification commands:
- `.venv/Scripts/python -m pytest -q -p no:cacheprovider --basetemp local/pytest-<new>` (baseline 25 Oct: 1528
  passed, 1 skipped)
- `.venv/Scripts/python -m ruff check .`
- `.venv/Scripts/python -m mypy src/psp_buddy` (strict via pyproject)
- `node --test tests/node/*.mjs` (8 pass; after Task 4: pytest 1557 / 1 skipped)
- helper: `.venv/Scripts/python -m pytest -q -p no:cacheprovider --basetemp local/pytest-<new> local/move-attack-trial-20261017` (189 pass)

Every live task: AGENTS.md backup (SHA-256 verified, new timestamped folder), memstick SCREENSHOT folder exists,
graceful close, originals unchanged afterwards.

## Task 1 — [done 25 Oct] — Offline: reuse check and spirit ids from retained data

1. Confirm against PPSSPP 1.20.4 `Core/Debugger/WebSocket/*Subscriber.cpp` that no save-state event exists (else
   switch D4 to it and note it in the spec).
2. From the retained spirit dumps (m9livesp*, m11live*): list every (id, cost) in all 26 pilots' spirit lists and
   pick the pilots that hold unknown ids, so one screen visit can name Alert and Invincible.
Expected: a short list of pilots to visit; no code.
Result: no save-state event in 1.20.4. Hypothesis Alert = id 3 (bit 0x04), Invincible = id 5 (bit 0x10). Allies with
Alert: 149303184, 149304848; no ally has Invincible learned (only third-force Wing Gundam Zero 149299544, whose
status screen should name 5, 3, 7). See the spirit-recon note, 25 Oct section.

## Task 2 — Live view-only recon (protected)

Declaration `spirit_recon`; open the spirit list of the chosen pilots, screenshot each, Cross out. Then
`spirit_cast_recon` once for Alert and once for Invincible on a unit that does not matter for turn 7 (SP drop and
mask +0x14 before/after). Record ids, costs and mask bits in `docs/research/2026-10-23-spirit-recon.md`.

## Task 3 — [done 25 Oct, ids hypothetical until Task 2] — Spirit preference (TDD)

Files: `src/psp_buddy/spirits.py`, `src/psp_buddy/policy.py`, `tests/unit/test_spirits.py`, policy tests.
Red: Alert chosen when Sense/Focus missing; Invincible when only it is learned; SP short and active skip to the
next; Sense still first; new clause `use spirits before attacking` and the old alias. Green, then run checks.

## Task 4 — [done 25 Oct] — Protected units (TDD; no input, see spec D3)

Files: `src/psp_buddy/policy.py`, `plan_act.py`, `turn.py`, `info_navigation.py`, `tools/ppsspp_navigation_mcp.mjs`,
tests. Red: `protect:` clause parsing; a protected unit's `plan_act` sends only the Standby presses and records
`standby`; protected objects/names validated (Python + node). Green, checks.

## Task 5 — [done 25 Oct] — `retry.py` ledger and manifest (TDD)

Files: `src/psp_buddy/retry.py`, `tests/unit/test_retry.py`. Red: `next_step` done / retry (protected grows) / cap
after 3 retries / non-loss stops give up; `manifest` + `matches` (HP, EN, tile, turn, unmoved; one changed field
fails); report write error returned. Green, checks.

## Task 6 — Checkpoint save tool (local, then live)

`local/m12-tools/save_checkpoint.ps1` (+ Python wrapper): foreground, menu steps with a window capture per step,
new-file and hash checks, copy + `manifest.json` via `retry.manifest`. Live (protected): save at turn 7 start,
relaunch from it, `matches` passes. Expected: identical manifest after relaunch.

## Task 7 — Live retry run (protected)

Run: checkpoint at turn 7 start -> M9 loop with `use spirits before attacking` -> End Turn -> strict enemy phase.
On a loss: close, `next_step`, backup, relaunch with the checkpoint, `matches`, replay with the protected list.
To prove a reload when nothing is lost, one forced retry is allowed (agent-declared, recorded in the ledger).
Expected: turn 8 with no ally lost and `retry-report.json` listing every attempt; or a correct `give_up` ledger.

## Task 8 — Review and notes

Code review (high) over the M12 diff, fix Critical/Important red-first, rerun checks, update `docs/progress.md`
and the handover.
