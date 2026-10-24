# M11 Spirits and non-boss targets — implementation plan (23 Oct 2026, uncommitted)

Spec: [design](../specs/2026-10-23-spirit-boss-policy-design.md).

Verification commands (from earlier milestones):
- `.venv/Scripts/python -m pytest -q --basetemp local/pytest-<new>` (all pass, 1 skipped; launch tests fail with the
  default temp dir outside the workspace)
- `.venv/Scripts/python -m ruff check src tests`
- `.venv/Scripts/python -m mypy --strict src`
- `node --test tests/node/*.test.mjs` (8 pass; the bare directory form fails on Windows)
- helper tests: `.venv/Scripts/python -m pytest -q --basetemp local/pytest-<new> local/move-attack-trial-20261017` (185 pass)

## Task 1 — [done 23 Oct] — `spirit_recon` bridge purposes (TDD)

Files: `src/psp_buddy/info_navigation.py`, `tools/ppsspp_navigation_mcp.mjs`, `tests/unit/test_action_navigation.py`.
1. Red: test that `spirit_recon` allows `open_spirit` (Spirit highlighted), `spirit_pilot`, `spirit_menu_move`, `cancel`
   from spirit contexts, and refuses Circle in `spirit_list`, Move/Attack/Standby, `open_spirit` with another highlight,
   and an inexact declaration. Run: the new tests fail.
2. Green: contexts `spirit_pilots`, `spirit_list`; purposes as in the spec; declaration `["spirit_recon"]`.
3. Node: same contexts/purposes, `open_spirit` and `spirit_pilot` in Circle purposes, highlight "Spirit".
4. Run the verification commands.

## Task 2 — [done 23 Oct] — Live view-only recon (protected)

1. `action-declaration.json` = `{"unit":"Gundam 00","actions":["spirit_recon"]}` (old one kept as
   `action-declaration.act.json`); add `Gundam 00: 149303600` to the handoff's unit objects.
2. `restart.ps1 -Label m9livesp1` (graceful close, originals check, SHA-256 verified backup, launch).
3. Screenshot -> cursor to Gundam 00 -> open menu -> highlight Spirit -> dump -> `open_spirit` -> screenshot/dump ->
   browse rows -> dump -> Cross out to the map. No Circle in the spirit list.
4. Close gracefully, verify originals, record findings in `docs/research/2026-10-23-spirit-recon.md`.
Expected: the spirit list with costs (Focus 15, Sense 20 for Setsuna), its order, and whether a pilot screen appears.

## Task 3 — [done 23 Oct] — Offline decode of spirit data

From the dumps: Setsuna's spirit IDs/costs list, SP field (known), list order matching the screen, candidate active-effect
field (needs a cast; deferred to Task 6). Helper `weapons`-style reader `read_spirits(object)` with tests over the dump.

## Task 4 — [done 23 Oct] — Bosses and target order (TDD)

Files: `src/psp_buddy/tactics.py`, `src/psp_buddy/policy.py`, `src/psp_buddy/models.py`, tests.
Red tests: boss by name, by 2x median max HP, neither; non-boss first even when a boss is damaged; clause parsing.
Then `boss_names` through `plan_act`/`turn_next` (Python + node validation).

## Task 5 — Spirit choice and cast step (TDD)

Choice is done (`spirits.choose_spirit`). First a protected live **cast recon** (new declaration, e.g.
`spirit_cast_recon`, allowing one Circle on a declared spirit row of the trusted unit): screenshot after the Circle
(Yes/No?), RAM dump before/after, SP drop, then the map/command-menu state after the cast. Then the cast step.
Cast recon done 24 Oct: no Yes/No; back to the map, unit unmoved; SP drop = cost; mask +0x14 (Sense 0x44). The cast
step is therefore: goto unit, Circle (Command menu), Down x2 (Spirit, check the menu row), Circle, Down x row, Circle,
wait, read SP and mask (both must change as predicted, else `spirit_mismatch` / skip), then the usual act from the map.

Files: new `src/psp_buddy/spirits.py`, `src/psp_buddy/act.py` / `plan_act.py`, bridge purposes for the cast inside `act`.
Red tests: Sense first, Focus fallback, SP short, active, menu row; act stage order (spirit before move), SP-drop check,
skip on unconfirmed stage, `spirit_mismatch` stop.

## Task 6 — Live turn 7 and turn 8

1. Protected run of the M9 loop with the new policy to `done`; check the report for spirits and order.
2. Strict M10 End Turn + enemy phase to turn 8.
3. Code review (high), fixes, notes, progress, handover. No commit unless asked.
