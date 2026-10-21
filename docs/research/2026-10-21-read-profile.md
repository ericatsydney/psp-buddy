# Read profile (M7 task 1, offline part) — 21 Oct 2026

Source: `act_read` entries in `agent-navigation-inputs.jsonl` of runs act4, act5 and m6 (under
`local/move-attack-trial-20261017/`). No emulator was launched for this note.

## Findings

- Reads fall into two clusters: **about 1.0 s** (0.88-1.06) and **about 14-19 s**. Nothing in between.
- 1.0 s is the cost of one `observation_pause` (cpu.stepping + status polls + resume) plus a small read
  (`_read_menu_row`, `_read_hit`, baseline-based `_read_weapons`).
- The 14-19 s reads are the full `read_state` (and `_read_targets`), which call `collector.collect_observation`.
  That path runs inside one pause and does: 26 anchor checks via `read_original_code` (`replacements:false`),
  `version` and `game.status` requests, about 8 batched fetches including the 224x104 B pool, 16 KB actor
  catalogue, and a chain of 10+ sequential `follow()` fetches (8 B each, one websocket round trip each),
  then a second pause for the map (24x34x16 B cells).
- Totals: act4 sum of reads 73 s of 86 s span (13 reads); m6 36 s of 87 s (9 reads); act5 270 s of 350 s (37 reads;
  this run had retries). Presses (about 8-19 per run) are cheap; the rest of the span is settle sleeps and
  screenshots.

## Live step timing (21 Oct, run spd1-run-20261021T1931, view-only, one `read_state`)

Backup backups/spd1-original-20261021T092837Z-* (44 files, SHA-256 verified); PPSSPP closed gracefully;
originals 44/44 unchanged afterwards. Timer wrapper: `local/move-attack-trial-20261017/timing_handoff.py`
(wraps `DebuggerAdapter._exchange`; log `timing.jsonl` in the run folder).

One `read_state` = 15.65 s:

| Part | Calls | Seconds |
|---|---|---|
| `memory.read` with `replacements:false` (original-code anchor reads) | 25 | 13.47 (about 0.54 each, size 16-436 B makes no difference) |
| `cpu.stepping` + `cpu.resume` (2 pauses) | 4 | 2.05 (about 0.5 each) |
| `memory.read` with `replacements:true` (all data blocks, pool, catalogue, follows, map) | 42 | about 0.0 |
| `version`, `game.status`, `cpu.status` | 11 | about 0.0 |

**Conclusion:** the whole cost is the 25 anchor code reads (a fixed latency per `replacements:false` read, not
size) plus 2 pauses at about 1 s each. Ordinary data reads are effectively free, so reading more data in one
state read costs nothing.

## Lean-read design (feeds M7 task 2)

- Verify the anchors once per session (code is immutable) and skip them in later reads: `read_state` drops to
  about 2-3 s (two pauses plus data reads). Keep identity/anchor verification at session start and after any
  scene reload, and keep the fail-closed behaviour if the one-time verification failed.
- Merge the map read into the same pause as the unit read: about 1.5 s per state read.
- A narrow `read_actor` is then optional; a full state read may be cheap enough for every poll.
- Expected act time: reads about 10 x 1.5-2.5 s instead of 6 x 15 s, so the 30 s target is plausible from the reads alone.

## Live result of the lean reads (21 Oct, run spd4-run-20261021T2046, view-only)

Backup backups/spd4-original-20261021T104645Z-* (44/44 SHA-256); PPSSPP closed gracefully; originals 44/44 unchanged.
(An earlier run, spd3, failed only because my timing wrapper dropped the new keyword arguments; nothing was sent to the game.)

- Every read after the baseline took **1.0-1.15 s** (7 `read_state`: 1.10-1.14 s; 11 `act_read`: 1.02-1.13 s).
  Before: 14-19 s. The anchor code reads happen only in the baseline (50 original-code reads in the log, all before ready).
- Plan-stage refusal (`unknown_weapon`) returned in 2.3 s total. `act commit:false` (Destiny move to (19,6), FlashEdge2 on Mercurius)
  reached the forecast in **24.5 s** (was about 70 s): select, move (EN 230 to 229), weapon row 2, target (18,8), hit 60 shown, all memory-checked.
  Fire phase not timed (not requested; nothing confirmed).
- Weapon names in the instruction carry no spaces (`RQM60FFlashEdge2`); the plan stage lists the valid names when it refuses.
- Screenshots are single-use per act call (refused otherwise): one grounding screenshot per act, about 3 s by PowerShell.
- Left: 11 reads is about 12 s of the 24.5 s, so the remaining time is reads plus press/settle sleeps. Task 3 (fewer reads and blind presses
  after passed memory checks) and the fire phase's two polls are the next savings; the under-30-s target includes fire.

## Fired act timing (21 Oct, run spd5-run-20261021T2112, backup spd5-original-20261021T111256Z-*, 44/44; originals unchanged after graceful close)

Destiny move (19,5)->(19,6), RQM60FFlashEdge2 on Mercurius (60% forecast, matched the screen), fired on the trial copy:
- act to forecast (`commit:false`): **24.6 s**; fire phase (`phase:"fire"`, Start + result): **20.5 s**; plus two PowerShell screenshots (about 3.5 s each).
  Total about **45 s of act time** (about 52 s with screenshots), against about 160 s before. The under-30-s target is **not yet met**.
- Fire memory facts: EN 229 -> 224, action counter 1 -> 0, counted_as_unmoved true -> false; Mercurius EN 140 -> 135 (counter fire);
  Mercurius HP not changed in the reported deltas (EN only).
- Where the rest goes (about 11 reads at 1.1 s = 12 s in the forecast phase, a fire poll loop, settle sleeps): next savings are task 3
  (skip redundant reads after a passed check, shorter settles), measured per stage with the same timer.
