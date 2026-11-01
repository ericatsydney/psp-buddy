# Fast screenshots — implementation plan

Spec: `docs/superpowers/specs/2026-11-01-fast-screenshots-design.md`. Nothing is committed.
Start only after live run fr-s33b has finished (no screenshot code changes during a live run).

## Verification commands

As in `docs/superpowers/plans/2026-11-01-faster-reads.md`, plus
`.venv/Scripts/python -m pytest -q -p no:cacheprovider --basetemp local/pytest-fs-<name> local/m9-tools/test_fast_shot.py`.

## Task 1 — tests first (`local/m9-tools/test_fast_shot.py`)

Fake window layer records calls (`find`, `restore`, `front`, `keys`) and, on `T`, writes a JPEG into the
temp folder (optionally in two parts across polls). Fake clock/sleep. Tests: new file returned with
SHA-256; older files ignored; half-written file waited for; timeout → `NO NEW SCREENSHOT`; call order;
no window → error. See them fail (module missing).

## Task 2 — `fast_shot.py`

`Win32` class (ctypes): `find()` via process snapshot (`CreateToolhelp32Snapshot`) + `EnumWindows`
(visible top-level window of that PID), `restore(h)` (`ShowWindow` 9), `front(h)` (Alt tap via
`keybd_event`, `SetForegroundWindow`), `keys(...)` (`keybd_event` Alt+D, then T). `shot()` as specified.
Green tests, ruff on the file.

## Task 3 — wiring

`local/m9-tools/turn_loop_lib.shot()` → `fast_shot.shot()`. `local/m15-tools/run.py`: timed shot wrapper,
`report['shots']`; test in `test_run.py` first. Full verification list.

## Task 4 — live check

In the next stage-33 run (`run.py m15-s33 --label fs-s33a`, its usual backups and CPU gate): report
`shots.median` < 1.5 s, no screenshot refusals in the mailbox responses, outcomes compared with fr-s33b.

## Task 5 — review and notes

Code review of the diff, fix Critical/Important, update `docs/progress.md`.
