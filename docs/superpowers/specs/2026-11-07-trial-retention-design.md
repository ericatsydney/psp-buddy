# Trial file retention — design

Date: 7 Nov 2026. Status: approved by the user 7 Nov ("好", after the manual clean-up).

## Problem

Every launch leaves two large copies behind that nothing reads again:

- the previous runtime, renamed to `local/runtime/ppsspp-v1.20.4-archive-<hex>` (about 165 MB);
- the trial's writable copy `backups/verified-snapshots/<trial>/working` (about 230 MB).

By 7 Nov there were 187 archives and 206 working copies (about 55 GB), and drive C: was full.
The user deleted all but the newest 5 of each by hand and asked for the same rule in code.

## Reuse check

No library is needed: `shutil.rmtree` and the existing owned-runtime marker and trial-id format
are enough.

## Rule

At the end of a successful `Launcher.prepare` (`src/psp_buddy/launch.py`), new module
`psp_buddy.retention`:

- `prune_runtime_archives(runtime_root, keep=5, protect=...)`: siblings named
  `<runtime name>-archive-<32 hex>` that are real directories (no link or junction) and hold the
  owned-runtime marker `.psp-buddy-runtime`. Newest first by the marker's mtime; delete all but
  `keep`. The archive this prepare just made is never deleted.
- `prune_working_copies(backup_root, keep=5, protect=...)`: children named like a trial id
  (`YYYYMMDDTHHMMSSffffffZ-<32 hex>`), newest first by name. For all but `keep`, delete only the
  `working` sub-folder. The `snapshot`, manifests and the trial folder itself are never touched.
  The current trial is never deleted.

Excluded: verified snapshots, portable-memstick backups, other backups, pytest folders.

## Failure behaviour

Best effort: an error deleting one folder (a locked file) is recorded and the rest continue.
Pruning never raises and never blocks the launch. `prepare` keeps the result on
`Launcher.last_prune` for the caller to report.

## Acceptance criteria

1. Unit tests: keeps the newest 5 and the protected one; ignores unrelated names, folders without
   the marker and links; deletes only `working`; an error is recorded and the rest continue.
2. `Launcher.prepare` with a runtime prunes archives and working copies beyond 5.
3. `pytest`, local tool tests, `ruff` and strict `mypy` pass.
