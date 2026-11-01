# M15 design — real-test readiness

Approved by the user 31 Oct 2026 (Australia/Brisbane), approach A "prepare offline, confirm live". Leave this
spec and its plan uncommitted; committing is the user's call.

## Goal

The user picks one of their PPSSPP save-state slots, runs one command, and the non-boss clear runner either
clears the non-boss foes or hands over cleanly, with no manual step. Today the runner works only on two prepared
checkpoints (`turn7-start`, `stage33-slot2`) with a hand-written manifest and a back-out pressed by hand with a
screenshot before each press ([31 Oct handover](../../research/2026-10-31-m14-handover.md)).

## User decisions (31 Oct)

- Input is a **PPSSPP slot number** (`ULJS00460_1.01_<N>.ppst` in the user's `PPSSPP_STATE`). No in-game
  SAVEDATA boot, no arbitrary paths.
- A save that opens on a screen memory cannot identify: **stop and press nothing**, report it with a screenshot.
- When the per-turn cursor budget (kept at `MAX_GOTO_PRESSES = 400`) will not cover the next action:
  **hand over mid-turn** on the map with no menu open, listing the allies that have not moved.
- P5 (menu entry counts from memory) is a stretch task; P1-P4 and the P6 real test are required.

## Reuse check

- mcp-ppsspp 0.2.0 (reviewed 15-17 Oct, `docs/workflow.md`): typed/range reads only; no save-state, decode or
  game-rule tools. Not used for M15.
- Offline state unpack already exists as a private research helper
  (`local/state-memory-20261016/extract.py`: revision 5 / Snappy, fail-closed, bounded) and was used on the
  stage-33 slot on 26 Oct with the project collector on the RAM image (all code-anchor checks passed). M15 reuses
  it rather than writing a new parser.
- Checkpoint manifest, retry block and live `check`: `local/m12-tools/checkpoint.py`, `psp_buddy.retry`.
  The helper already takes a checkpoint's fixture as its anchor ally (`handoff.apply_checkpoint_fixture`).
- Launch, verified backup, originals-unchanged check: `local/m9-tools/restart.ps1` (launched detached via WMI).
- Runner: `local/m13-tools/clear_loop.py` on `psp_buddy.clear`/`turn`/`plan_act`/`act`.

## Approaches considered

- **A. Prepare offline, confirm live (chosen).** Everything about the save is worked out from an offline copy
  before PPSSPP starts; live reads must agree before any press. Bad or unsupported saves are refused with nothing
  launched; the helper's identity check is unchanged; screen detection is testable offline. Risk: the offline
  unpack must handle every slot (only revision 5 / compression 1 proven).
- B. Discover live: the helper starts without a fixture. Weakens the helper's identity check, needs a protected
  launch to learn whether a save is usable, harder to test. Rejected.
- C. A with B as fallback: double code for an unseen case. Rejected; an unsupported unpack refuses instead.

## Scope

In: P1 prepare from a slot; P2 opening-screen classification and automatic back-out; P3 press estimates, skipped
redundant walks and `turn_budget` handover; P4 one-command launcher and final report; P6 real test on 2-3 slots.
Stretch: P5 menu entry counts from memory.

Out: in-game SAVEDATA loading, title/load menus, boss fights, Spirits beyond today's policy, copying trial saves
back to the user's memory stick, raising the 400-press budget, retries after a loss.

## Architecture

Pure logic goes in `src/psp_buddy` with unit tests; orchestration stays in ignored `local/m15-tools`, matching the
M9-M14 split.

| Piece | Where | Role |
| --- | --- | --- |
| `slot_prepare.py` | `src/psp_buddy` | choose the anchor ally and build the manifest from collected units (pure) |
| `screen.py` | `src/psp_buddy` | classify the opening screen from named memory fields; plan the back-out (pure) |
| `press_budget.py` | `src/psp_buddy` | estimate cursor presses for an action; decide fit vs `turn_budget` (pure) |
| `clear.py`, `turn.py` | `src/psp_buddy` | new outcome `turn_budget`; consult the estimate before each `plan_act` |
| `info_navigation.py` | `src/psp_buddy` | skip the map-proof walk when the cursor read already proves the tile; message says "turn" |
| `prepare.py` | `local/m15-tools` | `prepare --slot N [--name X]`: copy, hash, unpack, collect, classify, write manifest |
| `backout.py` | `local/m15-tools` | live: classify, one cancel press, re-classify, until `map`; then cursor walk to anchor |
| `run.py` | `local/m15-tools` | `run <checkpoint>`: CPU gate, launch, check, back-out, clear loop, report |

### P1 — prepare from a slot

`prepare.py --slot N [--name X]` (default name `slot<N>-<yyyymmddThhmm>`):

1. Refuse unless `PPSSPP_STATE\ULJS00460_1.01_<N>.ppst` exists. Copy it (read-only on the source) to
   `local/checkpoints/<name>/`; refuse if the folder exists. Record SHA-256 of source and copy; they must match,
   and the source hash is re-read after copying (unchanged).
2. Unpack the copy offline with the existing extractor into the checkpoint folder (ignored): user RAM at
   0x08800000. Unsupported revision/compression, bad lengths or cookies refuse.
3. Run the project collector on the RAM image with code anchors verified. The code anchor must be found exactly
   once.
4. `slot_prepare.choose_anchor(units)`: living (`hp > 0`) allies (menu-group side `byte // 4 == 0`) whose
   (object, mech_id, pilot_id) is unique; pick the lowest object. None → refuse `no_anchor_ally`.
5. `slot_prepare.manifest(...)` writes `manifest.json` in today's format: `file`, `sha256`, `source`, `at`,
   `stage` (when decodable), `fixture` {object, mech_id, pilot_id, hp, en, sp}, `fixture_source`, `retry`
   (`retry.manifest`), plus new `opening` {screen, backout} from P2 and `prepared_by: "m15 prepare"`.
6. Refuse if the RAM shows no player phase (enemy phase, cut-scene) — reported as `not_player_phase`.

The helper and `checkpoint.py check` read this manifest unchanged. A declaration naming "Destiny" already means
"the checkpoint anchor" (31 Oct), so the runner works whichever ally is the anchor.

### P2 — opening screen and automatic back-out

`screen.classify(fields) -> Screen` where `Screen` is one of `map`, `move_range`, `unit_commands`,
`post_move_menu`, `weapon_list`, `target_select`, `unknown`. `fields` is a small dict of named memory reads (the
same reads offline from the RAM image and live through the helper).

Known facts and gaps:
- The Command-menu slot 0x08E4BE34 keeps the last unit's menu after it closes (m14s33f), so slot contents alone
  do not prove a menu is open. The post-move menu has its own slot 0x08E4BEB4 (u32 count, u32 row; slots 0x80
  apart; wraps).
- No memory signature yet proves `weapon_list`, `target_select` or `move_range` open/closed. Plan Task 1 finds
  them offline from retained RAM dumps with screenshot labels (m14rec3's six dumps, M11/M12 recon dumps); if the
  retained dumps cannot separate the screens, one protected recon trial (screenshot + RAM dump per press) follows.
- A screen is supported only when its signature is backed by labelled evidence on at least two stages or two
  separate dumps. Everything else classifies `unknown`.

`screen.backout(screen) -> list[Step]` gives the cancel sequence (e.g. `target_select` → cancel → `weapon_list`
→ cancel → `unit_commands` → close_command_menu → `map`). A `post_move_menu` at start gets no back-out steps (it
is treated like `unknown`) unless Task 1 proves a cancel that undoes the move; the M14 Standby path is not used
at start-up because it spends the unit's action.

Live (`backout.py`): before each press, read fields and classify; the result must equal the expected screen of
the plan step, else stop `backout_unexpected_screen` with a screenshot. After each press, the classification must
be the next expected screen. At `map`, a cursor walk to the anchor tile proves the map cursor (existing `goto`).
`unknown` at the start: stop `unknown_opening_screen`, no press sent. At most 6 back-out presses.

### P3 — long turns in the 400-press budget

- `press_budget.estimate(cursor, unit_tile, destination, target_tile) -> int`: Manhattan walks, cursor → unit,
  unit → destination, plus a fixed margin per action (calibrated from the m14s33n logs, recorded in the plan).
- Before each `plan_act`, `turn.py` compares the estimate with the presses left (`MAX_GOTO_PRESSES - used`).
  If it does not fit: no press, outcome `turn_budget` with `unmoved_allies` (objects and tiles), on the map with no
  menu open (the previous action's verified end state).
- `info_navigation` skips the map-proof walk when the live cursor read equals the needed tile and the screen is
  `map` (P2 classifier), saving presses on adjacent actions.
- The cursor-budget refusal text says "turn", not "trial" (31 Oct minor finding).

### P4 — one-command launcher

`run.py <checkpoint> [--label L] [--first-turn T]`:

1. CPU gate: sample until CPU < 35% for 10 s, max 10 min; else refuse `machine_busy`, nothing launched.
2. Require a `manifest.json` with `opening.screen` ≠ `unknown` (else refuse, nothing launched).
3. Launch `restart.ps1 -Label L -Checkpoint <checkpoint>` detached via WMI `Win32_Process Create` (it makes the
   verified backup and checks originals; a failed backup stops it). Wait for `navigation-ready` (timeout →
   `launch_failed`), create the memstick SCREENSHOT folder, then wait for CPU < 35% again.
4. `checkpoint.py check <checkpoint> 1` must print `MISMATCHES []`, else `checkpoint_mismatch`.
5. `backout.py`; then `clear_loop.py <first turn>` to a log.
6. Write `local/m15-runs/<L>/m15-report.json`: label, checkpoint, slot, backup folder and its verification line,
   originals-changed count, outcome (`cleared`, `turn_budget`, `defeat`, or a stop reason), turns played, kills,
   allies lost, unmoved allies (for `turn_budget`), final screenshot file and hash, timings. Print one summary line.

Every stop leaves PPSSPP on the trial copy (never the user's memory stick) and is named in the report.

### P5 — stretch: menu entry counts from memory

Read the unit Command menu entry count and labels from the menu slot when it is proven open (P2) instead of the
per-mech tables (Spirit row, Repair/Supply). An entry the runner cannot place hands over `unknown_menu`.

### P6 — real test

2-3 of the user's other slots, different stages, each prepared and run with one command; each result recorded in
progress notes with its report.

## Failure behaviour

Every refusal before launch writes nothing to PPSSPP folders and launches nothing. Every live stop leaves the game
on the trial copy with a named reason. The save-protection rules in `AGENTS.md` apply to every launch: a fresh
SHA-256-verified backup of SAVEDATA and PPSSPP_STATE with a manifest, made while PPSSPP is closed; never copy
trial saves back.

## Acceptance criteria

1. `prepare --slot 2` on the stage-33 save produces the same `sha256` and `retry` units as today's hand-written
   `stage33-slot2` manifest. Its anchor follows the lowest-object rule (on stage 33 that is object 149299024, not
   Destiny 149300168); the fixture values must equal that unit's offline read, and the live helper must accept
   it (Task 7). Refusals tested: missing slot, existing folder, unsupported unpack, anchor not found once, no
   living ally, not player phase.
2. `screen.classify` labels every retained, screenshot-labelled dump correctly, and returns `unknown` for
   synthetic field sets outside the signatures.
3. `press_budget` and `turn.py`: unit tests show `turn_budget` before an action that would not fit, no press
   sent, `unmoved_allies` listed; an action that fits runs as before.
4. `run.py` refuses `machine_busy` and `unknown_opening_screen` with nothing launched (unit tests with fakes).
5. Live: `prepare --slot 2` then `run` on stage 33 with no manual step ends `cleared` or `turn_budget`; backup
   54/54 verified, originals 0 changed; report and final screenshot written.
6. Live P6: 2-3 other slots, each ends with a named outcome and no menu open at handover, or a pre-launch refusal
   that names why.
7. All checks pass: pytest, helper tests, node, ruff, strict mypy. Review finds no Critical/Important issue.

## Tests

Red-first for every `src` change. Offline fixtures: labelled RAM-field sets extracted from retained dumps (kept
private under `local/`, with only small synthetic field dicts committed in tests). Orchestration (`prepare.py`,
`backout.py`, `run.py`) tested with fakes for the extractor, collector, helper `nav`, CPU sampler and launcher.
