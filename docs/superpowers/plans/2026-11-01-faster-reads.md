# Faster reads — implementation plan

Spec: `docs/superpowers/specs/2026-11-01-faster-reads-design.md`. Nothing is committed.

## Verification commands

- `.venv/Scripts/python -m pytest -q -p no:cacheprovider --basetemp local/pytest-fr-<name>`
- `.venv/Scripts/python -m ruff check .`
- `.venv/Scripts/python -m mypy src/psp_buddy`
- `node --test tests/node/*.mjs`
- helper: `.venv/Scripts/python -m pytest -q -p no:cacheprovider --basetemp local/pytest-fr-h<name>
  local/move-attack-trial-20261017` (one known intermittent failure: rerun before treating it as real)
- `local/m13-tools/test_clear_loop.py` and `local/m15-tools/test_*.py` with the same pytest command.

## Task 1 — tests first (`tests/unit/test_launch.py`)

Give `FakeInspector` a `calls` counter in `process()`. Add a fake clock passed to `Launcher(..., clock=...)`.
New tests:

1. `test_identity_is_rechecked_at_most_every_30_seconds`: start a session; reset counter; two
   `assert_bound()` calls at t+0 and t+29 → 0 inspector calls; at t+30 → 1 call.
2. `test_a_changed_identity_fails_at_the_periodic_check`: change identity, advance 30 s → `ValueError`
   match `identity`.
3. `test_an_exited_process_fails_at_once_without_inspection`: `process.stopped = True` → `ValueError`
   match `not running`, 0 inspector calls.
4. `test_an_override_file_fails_at_once`: create `installed.txt` → `ValueError` match `override`.
5. `test_claim_and_close_always_check_identity`: within 30 s, `claim_connection()` and `close()` each
   call the inspector.

Expected: 1, 5 fail (inspector called every time / `clock` argument unknown); 2-4 may pass already.

## Task 2 — code (`src/psp_buddy/launch.py`)

- `FULL_CHECK_SECONDS = 30.0`; `Launcher(..., clock=time.monotonic)` passes the clock to `LaunchSession`
  (through `_SESSION_ISSUERS` check unchanged; clock as a keyword argument).
- `LaunchSession.assert_bound()` → instant checks, then `self._check_identity()` when
  `clock() - self._identity_checked >= FULL_CHECK_SECONDS`.
- `_check_identity()` = today's inspector comparison; sets `_identity_checked` on success.
- `__init__`, `claim_connection`, `close` call the instant checks plus `_check_identity()`.
- Run Task 1 tests (green) and the full verification list.

## Task 3 — live check

Ask nothing new (approved in the spec). Close PPSSPP gracefully, CPU < 35%, then
`local/m15-tools/run.py m15-s33 --label fr-s33a` (detached through its WMI launch; restart.ps1 makes and
verifies the backups and refuses on mismatch). Afterwards compute the median `act_read` seconds and the
turn-5 player-phase time from `agent-navigation-inputs.jsonl`, and compare with m15s33b.

## Task 4 — review and notes

Code review of the diff, fix Critical/Important, update `docs/progress.md` with results and next step.
