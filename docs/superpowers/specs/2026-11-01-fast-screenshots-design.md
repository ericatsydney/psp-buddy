# Fast screenshots — design

Status: approved by the user, 1 Nov 2026. Follows the faster-reads change (same M15 speed-up work).

## Problem

Every mailbox operation (unit action, back-out press, End Turn, goto) carries a fresh screenshot reference
(`screen_file`, `screen_sha256`; `InfoNavigation._frame` and the stale-file rule). The presses inside one
action take none. A run on stage 33 takes about 46 screenshots. `local/m9-tools/shot.ps1` starts
PowerShell, compiles a C# helper (`Add-Type`), raises the PPSSPP window, opens the Debug menu (Alt+D, T)
and waits 3.4 s in fixed sleeps: about 5 s each (estimate), about 4 min per run.

## Reuse check

- Debugger render capture (`gpu.buffer.renderColor`, `DemandCapture`, `capture_handoff.py`) failed with
  "Could not download output" on PPSSPP 1.20.4 under Direct3D 11 and OpenGL (10 and 18 Oct): not used.
- Fewer screenshots would relax the helper's per-operation rule: not chosen.
- Chosen (user, 1 Nov): keep PPSSPP's own screenshot command, done faster.

## Design

New `local/m9-tools/fast_shot.py`, `shot(*, win=Win32(), folder=SCREENSHOTS, clock, sleep) -> (name, sha256)`:

1. List the files already in the trial's SCREENSHOT folder.
2. Through a small Windows layer (ctypes, user32/kernel32; replaceable in tests): find the
   `PPSSPPWindows64.exe` main window, restore it, bring it to the front (Alt tap, as shot.ps1), send
   Alt+D, wait 0.3 s, send T.
3. Poll every 0.1 s for a new `.jpg`. It is complete when its size is the same on two reads and the data
   ends with the JPEG end marker `FF D9`. Return its name and SHA-256.
4. No complete new file within 5 s → `ValueError('NO NEW SCREENSHOT')` (clear_loop's 3-try retry stays).
   No PPSSPP window → `ValueError('PPSSPP window not found')`.

`turn_loop_lib.shot()` calls `fast_shot.shot()`; `shot.ps1` stays for manual use.
`run.py` wraps the shot function with a timer and writes `shots: {count, median, max}` to the report.

Unchanged: the helper and its screenshot checks, the mailbox, backups, the press budget.

## Acceptance criteria

1. Unit tests (`local/m9-tools/test_fast_shot.py`, fake window layer, temp folder): returns the new file
   and its hash; ignores files present before; waits for a half-written file; times out with
   `NO NEW SCREENSHOT`; sends restore, front, Alt+D, T in that order; no window → error.
   `local/m15-tools/test_run.py`: the report carries shot count/median/max.
2. All verification commands pass.
3. Live, next stage-33 run (fresh verified backups, CPU < 35%, detached launch): every screenshot is
   accepted by the helper (no screenshot refusal), median screenshot time < 1.5 s, play as before.

## Exclusions

Debugger capture, fewer screenshots, battle animations off, skipping the repeated map proof.
