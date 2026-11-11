# Move range from the "can stop here" byte — plan

Spec: `docs/superpowers/specs/2026-11-10-stop-tile-move-range-design.md`. Nothing is committed
unless the user asks. Builds on the uncommitted `range_problems` logging.

Test command throughout (the temp folder must be inside the workspace, and no path argument, or
`tests/unit` and `tests/integration` clash on `test_debugger`):

`.venv\Scripts\python.exe -m pytest --basetemp local/pytest-stop -q`

Baseline 10 Nov: 1807 passed, 2 skipped.

## Task 1 — decode byte 2

Files: `src/psp_buddy/battle_state.py`, `tests/unit/test_battle_state.py`.

1. Failing tests: `decode_map` returns `stop_rows` from byte 2; `stop_tiles` lists marked tiles.
2. Add both. Update exact-dict expectations that now lack `stop_rows`.

## Task 2 — `act.stop_range`

Files: `src/psp_buddy/act.py`, `tests/unit/test_act.py`.

1. Failing tests: valid s2m-shaped state gives `[x, y, distance]`; `[]` when costs exist, screen is
   not `move_range`, `move` is not an int or is below 1, no tile is marked, own tile is marked, or
   a tile is beyond `move`.
2. Implement. `centered` is unchanged.

## Task 3 — planner

Files: `src/psp_buddy/tactics.py`, `tests/unit/test_tactics.py`.

1. Failing tests, state with empty costs and valid byte 2: advance; retreat; no attack planned
   after a move, even with a foe reachable from a marked tile; own-tile attack still planned; 2-foe
   rule still filters; turn-1 hold still holds; `expect.range_source == "stop_byte"`; a costed
   state has no `range_source` and still attacks after a move.
2. Pass `weapon_read.get("move")` to `_reachable`; fall back to `act.stop_range` and report the
   source; `_plan` leaves `moves` empty for the fallback.

## Task 4 — Move stage

Files: `src/psp_buddy/act.py`, `tests/unit/test_act.py`, `tests/unit/test_act_navigation.py`.

1. Failing tests: Move stage accepts a fallback destination on a move-only instruction, refuses one
   outside it (`destination_not_reachable`), still raises `range_not_centered_on_unit` when both are
   invalid or when the instruction has an `attack`, records `range_source`; a refused tile still
   gives `move_not_confirmed` unchanged (D1); `_post_attack_move` stays false on byte 2 alone.
2. Implement in the `_Run.move` stage; `read_weapons` only when the costed range was refused.

## Task 5 — honest skip and log

Files: `src/psp_buddy/plan_act.py`, `src/psp_buddy/turn.py`, `tests/unit/test_plan_act.py`,
`tests/unit/test_turn.py`.

1. Failing tests: both empty -> `move_range_unreadable`, classified as skipped; a real
   `no_target` with a valid range stays `no_target`; log record gains `stop_tiles` and
   `stop_range_valid`.
2. Implement.

## Task 6 — verify and hand over

1. Offline replay on `local/move-attack-trial-20261017/s2l-run-20261110T033634Z` where the log
   allows it.
2. Commands, expected all clean:
   - `.venv\Scripts\python.exe -m pytest --basetemp local/pytest-stop -q`
   - each local tool test folder, `local/m13-tools`, `local/m15-tools`, `local/m17-tools`
   - `.venv\Scripts\python.exe -m ruff check src tests`
   - `.venv\Scripts\python.exe -m mypy src`
3. `/code-review` on `git diff HEAD` and untracked files; fix Critical and Important findings.
4. Live trial only after fresh SHA-256-verified backups of both complete directories and the
   portable memstick, with PPSSPP closed (AGENTS.md). Check acceptance criterion 5.
5. Update `docs/features.md` and `docs/progress.md`. Remove `local/pytest-stop`.
