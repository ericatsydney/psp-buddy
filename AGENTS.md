# Project instructions

## Session progress reports

Before starting work in a new chat or on a new day, read `docs/progress.md` and the
latest handover. Give a short three-layer report: long-term goal and function
checklist; short-term game-rule/memory investigation checklist; today/session goal.
Tick only items ready within their stated scope. Keep blockers, test counts and
technical details out of this routine report unless the user asks. Update the notes
at session end. Use `docs/workflow.md` for research-efficiency and MCP lessons.
This reporting preference does not remove verification or save-protection duties.

## New-requirement flow (conflict gate)

For every new requirement or behaviour change, follow this order:

1. **Brainstorm** the requirement with the user (brainstorming skill, one question at
   a time, 2-3 approaches, explicit design approval).
2. **Document** it: spec in `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` and
   plan in `docs/superpowers/plans/YYYY-MM-DD-<topic>.md` (both left uncommitted).
3. **Engineering conflict review** before any implementation: run gstack
   `/plan-eng-review`, naming the new spec and plan paths explicitly as the target.
   Ask it to check the requirement against every existing and earlier feature:
   - `docs/features.md`, the compact register of existing behaviour and the user's
     standing decisions (start here; open a linked spec only where an entry is touched);
   - the open items in `docs/progress.md`;
   - the current code paths the plan touches and their tests;
   - this file's save-protection rules.
   Do not read the whole progress history; search it only for a specific entry.
   The review is read-only: it must not launch or control PPSSPP. Any live probe it
   proposes is a separate trial under the save-protection rules below.
4. **Challenge the user on every conflict found.** Do not resolve a conflict silently
   or pick a side. For each one, state the new requirement, the existing feature or
   earlier decision it clashes with (with file/section evidence), the impact, and the
   options (change the new requirement, change or retire the old behaviour, or keep
   both with a defined precedence). Wait for the user's decision.
5. Record the review result and each conflict decision in a `## Conflict review`
   section of the spec, update the plan if needed, and have the user review the final
   spec. If no conflict was found, say so in that section.
6. Only then implement (TDD), verify, code-review and hand over as usual.
7. When the work is done, update `docs/features.md`: add, change or retire the entries
   it affects, so the register stays the single compact list for the next review.

## Save protection

Before every trial or test that launches, controls, or changes PPSSPP or the game, create a fresh timestamped backup of both complete directories:

- `C:\Users\ericg\OneDrive\Documents\PPSSPP\PSP\SAVEDATA`
- `C:\Users\ericg\OneDrive\Documents\PPSSPP\PSP\PPSSPP_STATE`

Store backups under this project's `backups` directory. Include all files and subfolders, including STAGE.BIN, SYSTEM.BIN, metadata, thumbnails, .ppst files, and undo states. Verify every copied file against the source using SHA-256 and save a manifest. If copying or verification fails, do not proceed with the trial or test. Back up while PPSSPP is closed or otherwise confirmed not to be writing saves. Never overwrite earlier backups. Delete them only through `psp_buddy.retention`, which keeps the newest 5 complete cycles of verified snapshots, portable-memstick backups and `-original-` backups after a new backup is verified (user, 10 Nov). Never delete anything under `local\runtime\ppsspp-v1.20.4` or any runtime archive.

When testing with a separate portable memory stick, also back up its complete SAVEDATA and PPSSPP_STATE directories before each trial. Back up configuration before changing it. Keep verified backup snapshots separate from writable trial copies. Do not automatically copy trial saves back to the original memory stick.
