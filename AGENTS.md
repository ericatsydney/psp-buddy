# Project instructions

## Session progress reports

Before starting work in a new chat or on a new day, read `docs/progress.md` and the
latest handover. Give a short three-layer report: long-term goal and function
checklist; short-term game-rule/memory investigation checklist; today/session goal.
Tick only items ready within their stated scope. Keep blockers, test counts and
technical details out of this routine report unless the user asks. Update the notes
at session end. Use `docs/workflow.md` for research-efficiency and MCP lessons.
This reporting preference does not remove verification or save-protection duties.

## Save protection

Before every trial or test that launches, controls, or changes PPSSPP or the game, create a fresh timestamped backup of both complete directories:

- `C:\Users\ericg\OneDrive\Documents\PPSSPP\PSP\SAVEDATA`
- `C:\Users\ericg\OneDrive\Documents\PPSSPP\PSP\PPSSPP_STATE`

Store backups under this project's `backups` directory. Include all files and subfolders, including STAGE.BIN, SYSTEM.BIN, metadata, thumbnails, .ppst files, and undo states. Verify every copied file against the source using SHA-256 and save a manifest. If copying or verification fails, do not proceed with the trial or test. Back up while PPSSPP is closed or otherwise confirmed not to be writing saves. Never overwrite or delete earlier backups as part of testing.

When testing with a separate portable memory stick, also back up its complete SAVEDATA and PPSSPP_STATE directories before each trial. Back up configuration before changing it. Keep verified backup snapshots separate from writable trial copies. Do not automatically copy trial saves back to the original memory stick.
