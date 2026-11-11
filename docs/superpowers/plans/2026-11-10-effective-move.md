# Effective move value — plan

Spec: [effective move design](../specs/2026-11-10-effective-move-design.md). Implement only after the
conflict review decisions are recorded in the spec. No commits.

Verification commands (PowerShell, repo root):

```
.\.venv\Scripts\python.exe -m pytest --basetemp local/pytest-x -q
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m mypy src
```

Remove `local/pytest-x` afterwards. Local tool tests: `local/m13-tools`, `local/m15-tools`,
`local/m17-tools`, and the two `test_collector.py` files, each run separately. Expected: all pass.

## Task 1: bonus in `read_unit_weapons`

Files: `tests/unit/test_weapons.py`, `src/psp_buddy/weapons.py`.

1. Add the pilot runtime `+0x14` (2 bytes) and `+0x46` (2 bytes) segments to the `DESTINY` and
   `Z_GUNDAM_LIST` fixtures (Destiny pilot runtime `0x08EA8960`, Z `0x08EA57A8`): mask 0, will 100.
2. Write failing tests using the `probe` overrides on the skill bytes, will and mask: no skill gives
   stored move and bonus 0; skill 21 gives +1; will 129 gives +1; will 130 gives +2; flag `0x80` gives
   +3; flag plus skill 21 gives +4; `stored_move` stays the raw byte; no pilot gives bonus 0 and no
   read of `+0x14`. Run with `-k move` and expect failures on the missing keys.
3. Implement the constants and `_move_bonus`; return `move`, `stored_move`, `move_bonus`.
4. Run `-k weapons`. Expected: pass.

## Task 2: foe reach

Files: `tests/unit/test_tactics.py`.

A test that `foe_reach_of` on a read whose `move` is the effective value returns that value plus the
P-weapon range. Expected to pass with no production change; it pins the behaviour.

## Task 3: `range_source` in the turn report

Files: `tests/unit/test_turn.py`, `src/psp_buddy/turn.py`.

1. Failing tests: an advance whose `plan.expect` has `range_source: stop_byte` puts it in the entry; a
   normal advance's entry has no such key.
2. Add the key at the entry construction (`turn.py:63`), from `result["plan"]["expect"]`.

## Task 4: verification

1. Full tests, ruff, mypy, local tool tests.
2. Offline script from the s2o checkpoint: expected moves in spec criterion 2.
3. Offline: rebuild Hyaku Shiki's row from `s2o-run-20261110T100733Z/rejected-ranges.jsonl` and
   confirm `act.stop_range` accepts it with move 7 and refuses it with 6.

## Task 5: review and live trial

1. `code-review` skill on the working tree against this spec.
2. Live, after a fresh verified portable backup and the launcher's backup, PPSSPP closed first:
   `prepare.py --slot 1 --name s2p`, then `run.py s2p --label s2p`. Criterion 5. Afterwards close
   PPSSPP gracefully and hash OneDrive and the portable memstick against the pre-run manifests.

## Task 6: notes

Update `docs/features.md` (weapon read, stop-byte fallback, foe reach) and `docs/progress.md`.
