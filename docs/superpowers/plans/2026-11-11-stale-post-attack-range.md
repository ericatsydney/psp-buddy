# Stale Move range after a second attack — plan (Phase 1)

Spec: [design](../specs/2026-11-11-stale-post-attack-range-design.md). Implement only after the
conflict review decisions are recorded there. No commits.

Verification (PowerShell, repo root): `.\.venv\Scripts\python.exe -m pytest --basetemp local/pytest-x -q`
(remove `local/pytest-x` afterwards), `-m ruff check src tests`, `-m mypy src`, and the local tool
tests (`local/m13-tools`, `local/m15-tools`, `local/m17-tools`, the two `test_collector.py`), each
separately. Expected: all pass.

## Task 1: trace fields (`tests/unit/test_act.py`, `src/psp_buddy/act.py`)

1. Failing tests with `SimGame(post_attack_move=True)`: the result stage's trace entries have
   `screen` and `windows`; with `standby_ignored=True` the stop's `facts["trace"]` holds every read,
   not 8.
2. Add the two keys at `act.py:588`; pass `trace` instead of `trace[-8:]` in the two `_Stop` calls of
   `result`. Successful records keep `trace[-8:]`.

## Task 2: stop facts in the turn report (`tests/unit/test_turn.py`, `src/psp_buddy/turn.py`)

1. Failing test: a `failed` result whose `outcome` has `stage`, `reason` and `facts` gives a turn
   entry with `stop_facts` equal to those facts; other entries have no such key.
2. Add the key in `TurnLog.record`.

## Task 3: verify, review, live run

1. Full checks above; `code-review` on the working tree.
2. PPSSPP closed, fresh verified portable backup, then `prepare.py --slot 1 --name s2q` and
   `run.py s2q --label s2q` (the launcher makes its own verified backup). Afterwards close PPSSPP
   gracefully and hash OneDrive and the portable memstick against the pre-run manifests.
3. Read the windows from `turn-report*.json`; write the Phase 2 proposal into the spec.

## Task 4: notes

`docs/features.md` (diagnostic entry), `docs/progress.md`.
