# M13 plan — clear the non-boss foes, then hand over

Spec: [design](../specs/2026-10-25-nonboss-clear-handover-design.md) (approved 25 Oct). Leave this plan and
the spec uncommitted; committing is the user's call.

## Verification commands (same as M12)

- `.venv/Scripts/python -m pytest -q -p no:cacheprovider --basetemp local/pytest-m13-<name>` (baseline after
  M12: 1565 pass / 1 skipped)
- `.venv/Scripts/python -m ruff check .`
- `.venv/Scripts/python -m mypy src/psp_buddy` (strict via pyproject)
- `node --test tests/node/*.mjs` (8 pass)
- helper: `.venv/Scripts/python -m pytest -q -p no:cacheprovider --basetemp local/pytest-m13-h<name>
  local/move-attack-trial-20261017` (190 pass; one known intermittent failure, rerun before treating it as real)

Every task is offline until Task 6. Write each test first, see it fail for the right reason, then code it.

## Task 1 — `clear.py` (pure logic)

Files: `src/psp_buddy/clear.py` (new), `tests/unit/test_clear.py` (new).

Red tests first, using the unit-dict shape of `read_state` (`object`, `raw_menu_group_byte`, `hp`,
`max_hp`, `tile_x`, `tile_y`, `counted_as_unmoved`) and `turn: {"turn": n}`:
1. `begin` freezes the bosses: 5 foes (2 named Mercurius/Vayeate) → bosses = those 2. Then in a state with
   only those 2 alive, `nonboss_left == []` and `decide == "cleared"` (the median drift case).
2. A group-4 unit is neither a boss nor a non-boss.
3. A foe at HP 0 and a foe missing from the list both count as gone.
4. A late foe (new object) is a non-boss unless its name is in `BOSS_NAMES`.
5. `decide` priority: ally lost (`retry.lost_allies`) → `"ally_lost"`, even when cleared too.
6. `turn_budget`: start 7, budget 5 → turn 11 is `None`, turn 12 is `"turn_budget"`.
7. A state without units or turn → `ValueError`.
8. `handover_report` fields as in the spec (bosses with names from `mech_names`, allies, lost,
   nonboss_destroyed = non-bosses in start minus those left).

Run: `pytest tests/unit/test_clear.py` red, then implement, then green; ruff and mypy.

## Task 2 — `turn_next` clear field and handover lock

Files: `src/psp_buddy/info_navigation.py`, `tests/unit/test_act_navigation.py` (or the file holding the
existing `turn_next` tests; check with `grep -n turn_next tests/unit/*.py`).

Red tests first:
1. The first `turn_next` reads foe mech names (memory-only weapon reads into `_mech_names`), builds the
   `ClearRun`, and returns `clear` with `nonboss_left`/`bosses`/`turn`.
2. When the state has no non-boss foe left, the answer is `handover: {"reason": "cleared"}`, `unit_object: null`,
   `done: false`, and `handover.json` is written in the evidence folder.
3. After a handover: `press`, `goto`, `act`, `plan_act`, `probe_move`, `end_turn`, `enemy_phase` raise
   `ValueError` ("handed over"). `state`, `weapons`, `targets` and `observe` still work.
4. A turn stop (`TurnLog.stopped`) yields `handover: {"reason": "stopped:<reason>"}`.
5. A write error on `handover.json` is reported (`report_error`) and never raised; the lock still holds.

## Task 3 — new player turn after an enemy phase

Files: `src/psp_buddy/info_navigation.py`, `tests/unit/test_end_turn.py`.

Red tests first:
1. After `enemy_phase` returns `done`: `_end_phase` is None, the TurnLog is new, `plan_act` and
   `end_turn open` (after `turn_next` reports done) are allowed again.
2. The per-turn budgets listed in the spec start from 0 for the new turn. Taps and dumps do not reset.
3. `turn-report-<T>.json` and `enemy-phase-report-<T>.json` are kept per turn; `turn-report.json` is the current turn's.
4. After `enemy_phase` `stopped`: no reset, inputs stay refused; the next `turn_next` hands over with
   the stop reason (e.g. `ally_destroyed`).
5. The 7th player turn (`MAX_PLAYER_TURNS = 6`) refuses input.
6. The next `turn_next` after the reset applies `decide`, so `turn_budget` fires at turn start + 5.

## Task 4 — node tool and helper wiring

Files: `tools/ppsspp_navigation_mcp.mjs`, `tests/node/navigation_mcp.test.mjs`,
`local/move-attack-trial-20261017/navigation_handoff.py` (ignored) and its helper tests if the handoff
filters answers.

1. `ppsspp_turn_next` description: "... a `handover` answer means stop: no further input is accepted." The schema is unchanged.
2. Node test: the description and the passthrough of `clear`/`handover` (red first).
3. Find out how a helper session ends today (`restart.ps1`, `close_verify.ps1`, the handoff's shutdown).
   Write down whether the helper can exit and leave PPSSPP running. If it can't, the handover leaves the helper
   idle with inputs refused, and the spec's risk note is updated with what was found.

## Task 5 — driver `local/m13-tools/clear_loop.py`

Ignored folder; it reuses `local/m9-tools/turn_loop_lib.py` (`nav`, `shot`) and the policy text of
`m12_loop.py` (`cheap weapons below 20%; strongest boss weapons above 0%; target non-bosses before bosses;
use spirits before attacking`).

1. The loop as in the spec (turn_next → plan_act per unit → End Turn open/confirm with screenshots → strict
   enemy_phase until not `continue` → repeat). It carries over the M12 retry of a refused `turn_next` (5 tries).
2. On a handover: one screenshot, `handover-final.json` = `handover.json` + `screen` {name, sha256} +
   `screen_state` ("map" or "after_stop"), and a one-line summary.
3. Dry run against a fake `nav` (scripted answers) in a small test in `local/m13-tools/test_clear_loop.py`.
   It covers: cleared mid-turn, a turn → End Turn → next turn, ally lost in the enemy phase, and `turn_budget`. No emulator.

## Task 6 — review, notes, handover (offline)

1. Run all verification commands; record the counts.
2. Run the code-review skill (high) on `git diff HEAD` plus the new untracked files. Fix Critical/Important red-first and rerun.
3. Update `docs/progress.md` (M13 entry, next step) and write `docs/research/2026-10-2x-m13-handover.md`.

## Task 7 — live acceptance (later session, user present)

Before launch: `backup_only.ps1 -Label m13live1` (SAVEDATA + PPSSPP_STATE, 54/54 SHA-256), the SCREENSHOT folder
exists, PPSSPP is closed. Launch from `local/checkpoints/turn7-start` (hash-checked, never into the
memstick). The relaunch must give `retry.mismatches == []`. Run `clear_loop.py`.

Expected: the run hands over `cleared`, probably during turn 7 (m12try1 ran out of non-boss targets there), with
no ally lost. The game is on the map with no menu open. `handover-final.json` bosses match the screen (Mercurius, Vayeate
alive). PPSSPP is left open for the user. Before any later trial, the user closes PPSSPP gracefully (or allows the agent
to), and the originals are checked unchanged against the backup.

If the run does not clear in turn 7 (different luck or forecasts), turn 8 tests the new player-turn reset live.
Watch the turn start for dialogues (`scene_at_new_turn`).
