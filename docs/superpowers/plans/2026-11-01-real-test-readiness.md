# M15 plan — real-test readiness

Spec: [design](../specs/2026-11-01-real-test-readiness-design.md) (approved 31 Oct, approach A). Leave this plan
and the spec uncommitted; committing is the user's call. Branch: `m14-stage33` (d24d700) unless the user says
otherwise.

## Verification commands (same as M13/M14)

- `.venv/Scripts/python -m pytest -q -p no:cacheprovider --basetemp local/pytest-m15-<name>` (baseline 31 Oct:
  1628 pass / 1 skipped)
- `.venv/Scripts/python -m ruff check .`
- `.venv/Scripts/python -m mypy src/psp_buddy` (strict via pyproject)
- `node --test tests/node/*.mjs` (8 pass)
- helper: `.venv/Scripts/python -m pytest -q -p no:cacheprovider --basetemp local/pytest-m15-h<name>
  local/move-attack-trial-20261017` (195 pass; one known intermittent failure, rerun before treating it as real)
- `local/m13-tools/test_clear_loop.py` and new `local/m15-tools/test_*.py` with the same pytest command.

Tasks 1-6 are offline. Write each test first, see it fail for the right reason, then code it. Do not run long
recursive greps over `local/` while a trial is launching (they starve the backup gate, m14s33d).

## Task 1 — screen signatures from retained evidence (research, no code in src)

Question: which memory fields tell `map`, `move_range`, `unit_commands`, `post_move_menu`, `weapon_list` and
`target_select` apart at the moment of a screenshot?

1. List retained RAM dumps with a matching screenshot label: m14rec3 (six dumps, Destiny's post-move menu), the
   M11/M12 recon runs, the turn-7 and stage-33 checkpoint RAM images (opening screens: `turn7-start` map?,
   `stage33-slot2` move range). Record each (dump, screen) in `local/m15-screens/labels.json`.
2. Diff dumps across screen pairs within one run (fields that change only with the screen), then confirm on a
   second run or stage. Start from the known menu slots (0x08E4BE34, 0x08E4BEB4, slots 0x80 apart) and the cursor
   and selected-unit fields already bound in `info_navigation`.
3. Write `docs/research/2026-11-XX-m15-screen-signatures.md`: each screen's fields, values, evidence, and the
   screens still unproven.

Stop condition: every screen either has a signature seen on two dumps, or is marked unproven. If
`move_range`, `unit_commands`, `weapon_list` or `target_select` stays unproven, run **Task 1b** before Task 3.

Task 1b (only if needed) — one protected recon trial: backups per `AGENTS.md`; CPU < 35%; launch
`stage33-slot2` detached; for each screen, screenshot + RAM dump before and after one press (move range →
cancel; open Command menu → Attack → weapon list → target select → cancel ×3). Then repeat Task 1 steps 2-3.

## Task 2 — `slot_prepare.py` (pure)

Files: `src/psp_buddy/slot_prepare.py`, `tests/unit/test_slot_prepare.py`.

Red tests: `choose_anchor` picks the lowest-object living ally with a unique identity; skips dead, non-ally
(group side ≠ 0) and duplicate identities; raises `PrepareRefused("no_anchor_ally")` when none. `manifest()`
returns today's keys plus `opening` and `prepared_by`, with `retry` equal to `retry.manifest(state, sha256)`.
Then implement. Expected: new tests pass; full suite green.

## Task 3 — `screen.py` (pure)

Files: `src/psp_buddy/screen.py`, `tests/unit/test_screen.py`.

Red tests from Task 1's signatures (small synthetic field dicts copied from the labelled dumps): each labelled
case classifies correctly; mixed or missing fields → `unknown`; `backout(screen)` returns the cancel steps and
their expected next screens; `unknown` and unproven screens return no steps. Then implement.

## Task 4 — `press_budget.py` and `turn_budget` (pure + turn wiring)

Files: `src/psp_buddy/press_budget.py`, `tests/unit/test_press_budget.py`, `src/psp_buddy/turn.py`,
`src/psp_buddy/clear.py`, `src/psp_buddy/info_navigation.py`, their existing tests.

1. Calibrate the per-action margin from `local/m14s33n-loop.log` (presses used per `plan_act` vs Manhattan
   walks); record the number and its source in the research note.
2. Red tests: estimate = walks + margin; `turn` stops with `turn_budget` (no press, `unmoved_allies` listed)
   when the estimate exceeds presses left; actions that fit behave exactly as before (existing tests unchanged);
   `clear` maps `turn_budget` to a handover, not an error; the refusal text says "turn".
3. Red test in `test_act_navigation`/info-navigation tests: the map-proof walk is skipped when the cursor read
   equals the needed tile and the screen reads `map`; still walked otherwise.
4. Implement; full suite, ruff, mypy.

## Task 5 — `local/m15-tools/prepare.py`

Files: `local/m15-tools/prepare.py`, `local/m15-tools/test_prepare.py`.

Wraps `local/state-memory-20261016/extract.py` (import its functions; do not copy the parser) and the project
collector. Red tests with fakes: missing slot, existing folder, source hash changed during copy, unsupported
unpack, anchor found ≠ 1, not player phase → each refuses with its reason and leaves no partial folder;
success writes the manifest. Then a real offline run:

`.venv/Scripts/python local/m15-tools/prepare.py --slot 2 --name m15-s33-check` → compare with
`local/checkpoints/stage33-slot2/manifest.json`: sha256 and retry units equal; fixture = object 149299024's
offline read (lowest-object anchor); opening = the stage-33 opening screen from Task 1. Reads the user's `PPSSPP_STATE` copy-only; no emulator.

## Task 6 — `backout.py` and `run.py`

Files: `local/m15-tools/backout.py`, `local/m15-tools/run.py`, `local/m15-tools/test_backout.py`,
`local/m15-tools/test_run.py`; helper `local/move-attack-trial-20261017` gains a `screen_fields` read (helper
test first) if Task 1 needs fields the helper does not already read.

Red tests with fakes: back-out stops `backout_unexpected_screen` when a read disagrees, sends nothing on
`unknown`, caps at 6 presses, ends with the cursor walk; `run` refuses `machine_busy` (CPU fake) and
`unknown_opening_screen` before launching, stops `launch_failed` / `checkpoint_mismatch` with a report, and writes
the report fields of the spec on each outcome. The launcher uses WMI `Win32_Process Create` (memory:
detached launch) and the existing `restart.ps1`. Then implement.

## Task 7 — live acceptance on stage 33

Backups per `AGENTS.md` are made by `restart.ps1`; confirm its 54/54 line and originals 0 changed.

`.venv/Scripts/python local/m15-tools/prepare.py --slot 2 --name m15-s33`
`.venv/Scripts/python local/m15-tools/run.py m15-s33 --label m15s33a --first-turn 5`

Expected: no manual step; outcome `cleared` or `turn_budget`; report + final screenshot written. If a live step
goes wrong, rerun that step with a screenshot before each press (memory: screenshot before press). Close PPSSPP
gracefully between trials.

## Task 8 — stretch P5 (only if Tasks 1-7 pass)

Menu entry count/labels from the menu slot when proven open; replace the per-mech tables in the Spirit and
Standby paths; unknown entries hand over `unknown_menu`. Red tests first; one live re-check on stage 33.

## Task 9 — P6 real test

Ask the user which 2-3 slots (different stages) to use. For each: `prepare`, `run`, record the report in
`docs/progress.md` and a research note. A pre-launch refusal is a valid recorded result; fix only within this
milestone's scope, else note it for M16.

## Task 10 — verify, review, hand over

All verification commands; `/code-review` on `git diff HEAD` plus untracked files; fix Critical/Important;
update `docs/progress.md` (2c ticks) and write `docs/research/2026-11-XX-m15-handover.md`. Nothing committed
unless the user asks.
