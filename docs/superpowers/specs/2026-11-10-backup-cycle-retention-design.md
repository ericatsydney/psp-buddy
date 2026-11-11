# Backup cycle retention — design

Date: 10 Nov 2026. Status: design approved by the user 10 Nov ("Yes, write specs"); conflict
review pending. Extends `2026-11-07-trial-retention-design.md`.

## Problem

`backups/` is 52 GB and grows by about 670 MB per live run: 214 verified-snapshot folders
(36.5 GB), 20 portable-memstick backups (2.3 GB) and 165 dated `-original-` backups. The 7 Nov rule
prunes only runtime archives and `working` copies. The user's instruction, 10 Nov: "keep newest 5
cycles of all 3 kinds, don't delete anything under
`C:\Users\ericg\code\psp-buddy\local\runtime\ppsspp-v1.20.4`". On evidence: "if no test is
pending on that, it's fine".

## Reuse check

No library needed. `psp_buddy.retention` already has safe directory checks, best-effort deletion
and the launcher hook. Windows Volume Shadow Copy and OneDrive history do not give per-run cycles.

## Rule

Three kinds under the `backups` folder, each pruned on its own to the newest 5 complete backups:

| Kind | Folder name | Complete when |
|---|---|---|
| Verified snapshot | `verified-snapshots/YYYYMMDDTHHMMSSffffffZ-<32 hex>` | has `manifest.json`, no `INCOMPLETE` |
| Portable memstick | `portable-memstick-YYYYMMDDTHHMMSSZ` | manifest is a non-empty list, no entry has `verified` false |
| Original saves | `<label>-original-YYYYMMDDTHHMMSSZ` with optional `-<32 hex>` | same |

Manifests are read as `utf-8-sig`, because `restart.ps1` and the portable backup write them with a
byte-order mark (checked 10 Nov); plain UTF-8 parsing would make every backup look incomplete and
nothing would ever be pruned.

Newest is decided by the timestamp in the name. Walking from newest to oldest, complete backups
are counted until 5 are kept; everything older of that kind is deleted, incomplete ones included.
An incomplete backup newer than the fifth is left alone and does not count.

Never deleted:

- anything under the active runtime (`local\runtime\ppsspp-v1.20.4`), enforced by an explicit
  overlap check as well as by the name rules;
- names matching none of the three kinds: the 10 Oct first backups,
  `20261104-061103-before-copy-state4`, `portable-ppsspp-v1.20.4`, all `-original-config-` folders;
- the current trial (`protect`);
- links, junctions and other reparse points.

Evidence: two local tests (`local/move-attack-trial-20261017/test_collector.py`,
`local/transition-trial-20261016/test_collector.py`) read the `user-evidence` folders of trials
`20261015T120025749948Z-0289b926396c4c3683c13be0b1f44c51` and
`20261015T065827988941Z-c31825d738e445cc9db4e7fa0ceb0173` (267 MB). Those two `user-evidence`
folders stay; the rest of those two trials goes. All other evidence goes with its cycle.

Runtime archives (`local\runtime\ppsspp-v1.20.4-archive-*`) are no longer pruned (D4): retention
stops touching `local\runtime` entirely, and `prune_runtime_archives` is retired. Each launch still
renames the active runtime to a new archive beside it; that is a rename, not a deletion. Archives
now grow by about 165 MB per run with no cap.

`prune_working_copies` is retired, since whole old trials now go; the 5 kept cycles keep their
`working` folder.

## Interface

`psp_buddy.retention`:

- `plan_backup_cycles(backups_dir, keep=5, protect=None, never=()) -> list[Path]`: pure selection,
  no deletion. Also serves the first clean-up list.
- `prune_backup_cycles(backups_dir, keep=5, protect=None, never=()) -> PruneResult`: deletes that
  selection, best effort.

`Launcher.prepare` calls it in place of `prune_working_copies`, with
`backups_dir = config.backup_root.parent`, only when `config.backup_root.name ==
"verified-snapshots"`, and `never=(runtime_root,)`. It replaces both 7 Nov prune calls;
`Launcher.last_prune` holds its result.

## When

At the end of a successful `Launcher.prepare`, after this launch's snapshot is verified. `restart.ps1`
has by then written the run's `-original-` backup, and the portable backup is made before it.
`restart.ps1` compares the originals with the newest `-original-` backup, which is always kept.

The first clean-up is special: about 48 GB in one go. Before any launch with this code, the exact
list from `plan_backup_cycles` is shown to the user, who confirms it, and it is then run once.

## Failure behaviour

Best effort as on 7 Nov: an undeletable folder is recorded in `PruneResult.failed`, the rest
continue, and pruning never blocks a launch. If a run's backup fails, the launch stops before
pruning, so older cycles stay.

## Acceptance criteria

1. Unit tests: 7 of each kind leave the newest 5; incomplete backups do not count and older ones
   go; timestamp order holds across labels and both name forms; protected, link, unrelated and
   `-original-config-` folders stay; the two `user-evidence` folders stay; a path inside `never` is
   refused; an error is recorded and the rest continue.
2. `Launcher.prepare` removes old cycles, keeps the 5 newest with `working`, and leaves every
   runtime archive in place.
3. Dry-run list reviewed by the user before the first deletion.
4. After the first clean-up: 5 of each kind remain and `verify_backups` of those 5 still matches
   their manifests; the two local tests still collect their data files.
5. `pytest --basetemp local/pytest-cycles`, local tool tests, `ruff`, strict `mypy` pass.

## Conflict review

`/plan-eng-review`, 10 Nov, read-only, against `docs/features.md`, the open items in
`docs/progress.md`, the touched code and tests, and the AGENTS.md save rules. Decisions by the user:

- **AGENTS.md "Never overwrite or delete earlier backups as part of testing"**: changed by the
  user's 10 Nov instruction. Rewrite to: keep the newest 5 complete cycles of the three kinds;
  deletion happens only through the retention code, after a new backup is verified.
- **features.md:113-115 "all verified snapshots are kept"** and the 7 Nov spec's exclusions:
  superseded by the same instruction.
- **D4, runtime archives** (features.md:113, 7 Nov rule of keeping 5): never prune them. This
  reverses the 7 Nov archive rule, at about 165 MB per run.
- `docs/progress.md` "Snapshot growth ... dedup is an open option": closed by this rule.

No conflict with: the 60 s backup receipt, the checkpoint hash checks, `restart.ps1`'s comparison
with the newest `-original-` backup (always kept), or portable-memstick backups before each trial.
Outside review was not run, since it would send project content to an external provider.
