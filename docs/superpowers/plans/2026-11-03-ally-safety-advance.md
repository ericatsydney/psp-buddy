# M16 ally safety (turn-1 hold, advance) — implementation plan

Spec: [design](../specs/2026-11-03-ally-safety-advance-design.md). Uncommitted; no commits unless asked.

## Verification commands

- `.venv/Scripts/python -m pytest -q -p no:cacheprovider --basetemp local/pytest-m16`
- `.venv/Scripts/python -m ruff check .`
- `.venv/Scripts/python -m mypy src/psp_buddy`

## Tasks (red test first in each)

1. **Policy clauses** — `models.Policy` gains `hold_unspirited_turn_one`, `advance_when_no_target`
   (default False); `policy.FLAG_CLAUSES` maps the two clauses. Tests in `tests/unit/test_policy.py`:
   each clause sets its flag; defaults off.
2. **tactics** — `spirited(pilot)`; `plan_attack(..., turn=None, spirited=False)`:
   held unit plans the current tile only and hands over `held_turn_one`; advance plan when nothing
   is reachable (closest tile to the nearest living foe; cost then tile tie-break; no move when not
   closer; overlay required; occupied tiles excluded; third force ignored). Tests in
   `tests/unit/test_tactics.py`.
3. **plan_act** — read pilot spirits once when a clause is on (errors -> not spirited), pass the
   turn and `spirited`; execute a move-only plan (`run_act`, then `_standby`), result phase
   `advanced`; held plans make no overlay read; cursor-budget check counts a move-only walk;
   `_standby` Circles without Up when the cursor is already on the last entry. Tests in
   `tests/unit/test_plan_act.py` on `SimGame`.
4. **turn** — `held_turn_one` skip; `advanced` -> `standby` / `stop`. Tests in
   `tests/unit/test_turn.py`.
5. **Local runner** — add the two clauses to `POLICY` in `local/m9-tools/turn_loop_lib.py` (ignored
   file; not committed).
6. Full checks, code review (high), progress notes.

Expected result: all suites green; existing tests unchanged.

## Amendment 3 Nov (m16-i feedback; spec "Amendment 3 Nov (run m16-i ...)")

7. **policy/models** — `strongest_above_percent`, `retreat_damaged`, `defend_at_hit_percent`
   clauses; tests in `test_policy.py`.
8. **tactics** — strongest rule; damaged unit: safe attack tiles ordered by threats, retreat plan,
   `retreat_stay`; tests in `test_tactics.py`.
9. **plan_act / turn** — cast before a retreat move and on `retreat_stay`; `retreat_stay` is a skip;
   `advanced` with rule `retreat` reports reason `retreat`; tests in `test_plan_act.py`, `test_turn.py`.
10. **end_turn / info_navigation / MCP** — `defend_at` (Def. row 1) in `_react`; enemy_phase arg and
    validator; tests in `test_end_turn.py`, `test_action_navigation.py`, `navigation_mcp.test.mjs`.
11. Runner policy + `defend_at`; checks (above plus `node --test tests/node`), review, live re-run.
