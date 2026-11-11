# Backup cycle retention — plan

Spec: `docs/superpowers/specs/2026-11-10-backup-cycle-retention-design.md`. Nothing is committed
unless the user asks. No deletion in `backups/` happens before Task 4's confirmation.

Test command: `.venv\Scripts\python.exe -m pytest --basetemp local/pytest-cycles -q`
(no path argument; temp folder inside the workspace). Baseline 10 Nov: 1807 passed, 2 skipped.

## Task 1 — selection

Files: `src/psp_buddy/retention.py`, `tests/unit/test_retention.py`.

1. Failing tests for `plan_backup_cycles`, using `tmp_path` folders of all three kinds: keeps newest
   5; incomplete handling; order across labels and both `-original-` forms; `-original-config-`,
   10 Oct-style and `portable-ppsspp-*` names ignored; links ignored; `protect` kept; a path inside
   `never` never selected; a manifest with a UTF-8 byte-order mark counts as complete; an entry
   with `verified: false` or unparsable JSON does not.
2. Implement with name patterns and manifest checks (`utf-8-sig`). Use `config.paths_overlap` for
   the `never` check.

## Task 2 — deletion and evidence

Files: same.

1. Failing tests: `prune_backup_cycles` deletes the selection; a selected trial in the two named ids
   loses everything except `user-evidence`; an `rmtree` error is recorded and the rest continue.
2. Implement. Remove `prune_working_copies`, `prune_runtime_archives` (D4) and their tests.

## Task 3 — launcher hook

Files: `src/psp_buddy/launch.py`, `tests/unit/test_launch.py`.

1. Update `test_prepare_prunes_old_archives_and_working_copies` to expect 5 whole trials and all 8
   runtime archives left (rename the test to match); add a case
   where `backup_root` is not named `verified-snapshots` and siblings stay. The fixture's
   `backup_root` is renamed with `dataclasses.replace` for the positive case. See them fail.
2. Replace both prune calls at the end of `Launcher.prepare` with `prune_backup_cycles`.

## Task 4 — first clean-up (needs the user)

1. Write the dry-run list from `plan_backup_cycles` to
   `local/backup-prune-2026-11-10.txt`, with counts and size per kind. No deletion.
2. Show the user; wait for an explicit yes, stating that deletion is permanent.
3. Run once with PPSSPP closed; report removed, failed and free disk. Re-verify the 5 kept per kind
   against their manifests.

## Task 5 — verify and hand over

1. Commands, expected all clean:
   - `.venv\Scripts\python.exe -m pytest --basetemp local/pytest-cycles -q`
   - local tool tests in `local/m13-tools`, `local/m15-tools`, `local/m17-tools`,
     and both `test_collector.py` files named in the spec
   - `.venv\Scripts\python.exe -m ruff check src tests`
   - `.venv\Scripts\python.exe -m mypy src`
2. `/code-review` on `git diff HEAD` and untracked files; fix Critical and Important findings.
3. Update the `AGENTS.md` save-protection line, `docs/features.md` retention entry and
   `docs/progress.md`. Remove `local/pytest-cycles`.
