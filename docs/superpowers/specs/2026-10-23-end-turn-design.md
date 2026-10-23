# M10 End Turn and enemy phase — design (23 Oct 2026; approved by the user in chat, uncommitted)

## Goal

After an M9 player turn reports `done`, end the turn, get through the enemy phase with the game's defaults, and stop once the
next player phase (turn T+1) has started, with a report of what the enemy did. Advances the long-term items "handle enemy
reactions" and "complete a battle" from one player turn to one full turn cycle.

## Decisions (user, 23 Oct)

1. Scope: one turn change only (End Turn -> enemy phase -> turn T+1 confirmed). Playing turn T+1 is not included.
2. Defender choices on enemy attacks: accept the game's default (the highlighted Start, usually Counter).
3. Unknown screens: advance blindly but bounded — Circle only, caps on presses and time, stop on suspicious memory.
4. End Turn only when `turn_next` says `done` (not `stopped`); answer Yes even with skipped units still unmoved.
5. Approach 1: one agent screenshot check of the system menu, memory drives the rest.

## Reuse check

No external tool plays this game. Reused: `read_state` (turn counter u16 0x08DF8ADC, units), `_goto` (memory-verified cursor
walk), the screenshot/mailbox gate, `TurnLog`, `turn-report.json`. Known from the 19 Oct trial (progress.md "Short-term B"):
Circle on an empty tile opens the system menu with EndTurn highlighted; Circle on EndTurn shows "Unmoved Units: N - End
phase? Yes/No" with Yes taken by Circle; the enemy phase advanced with 7 Circle presses (Circle also takes the highlighted
Start on enemy forecasts); the turn counter reads T through the enemy phase and T+1 once the player phase starts; allies'
counters reset to unmoved, EN regenerates. Existing screenshot-per-press purposes (`open_system_menu`, `end_turn`,
`advance_dialog`) stay as they are.

## Approaches

1. **Agent-checked menu, memory-driven rest (chosen).** One screenshot guards the only step that could hit the wrong menu.
2. Fully blind macro: fewer steps, but Circles on a mistaken screen could act on a unit.
3. Screenshot per press (18 Oct way): about 40 round trips, contradicts decision 3.

## Design

**D1 `src/psp_buddy/end_turn.py` (pure logic + async macro over a small IO protocol, like `act`).**
- `empty_tile(state)`: nearest tile to the cursor with no living unit on it (inside the map), or None.
- `async open_menu(io, state)`: walk the cursor to `empty_tile` (memory-verified), press Circle; returns
  `{ok, phase: "menu_open", tile, turn}` or a stop. No further presses.
- `async confirm(io, turn)`: Circle (EndTurn), wait, Circle (Yes); returns `{ok, phase: "ending", turn}`.
- `async advance(io, start_state, budget)`: loop: read state; if the turn counter is T+1 and every living ally reads unmoved
  in two consecutive reads -> `done`; else press Circle, wait `ADVANCE_PAUSE` (2.5 s). Stops: an ally's HP drops to 0 or a
  unit object disappears (`ally_destroyed` / `unit_lost`), the turn changes by anything but +1 (`turn_jump`), unreadable state
  (`unknown_state`), per-call caps (40 Circles or the call deadline) -> `{phase: "continue"}` (not a stop), whole-phase caps
  (100 Circles, 8 minutes) -> `phase_budget`. Returns presses used, turn before/after and per-unit HP/EN deltas against the
  state at End Turn.
- `report(...)`: `enemy-phase-report.json` content: turn before/after, done/stopped, presses, per-unit deltas, damaged and
  destroyed allies, evidence screenshot names.

**D2 Operations (helper).**
- `end_turn {sequence, screen_file, screen_sha256, context, phase}`:
  - `phase: "open"`: context `map`, fresh screenshot; refused unless the `TurnLog` says done and not stopped, no forecast
    is pending, and End Turn was not already done in this trial.
  - `phase: "confirm"`: context `system_menu`, fresh screenshot, `highlighted_entry: "EndTurn"` (agent-confirmed); only
    directly after a successful "open". A failed or abandoned "open" can be undone with the existing `cancel` purpose.
- `enemy_phase {sequence}`: memory + Circle only; only after a successful "confirm"; repeated until `done` or a stop.
- MCP tools `ppsspp_end_turn`, `ppsspp_enemy_phase` (node validation), mailbox `OPERATIONS`, deadline 120 s.
- `turn-report.json` gains `ended: true` after confirm; `enemy-phase-report.json` is rewritten after each `enemy_phase`
  call (write errors returned as `report_error`, never raised).

**D3 Loop (agent).** M9 loop until `done` -> fresh map screenshot -> `end_turn open` -> screenshot (check: system menu,
EndTurn highlighted) -> `end_turn confirm` -> repeat {`enemy_phase`, screenshot as evidence} until `done` or a stop ->
final map screenshot of turn T+1.

## Changes after live runs (23 Oct, user decisions)

- `accept_losses` (option 1): a destroyed or lost ally (destroyed allies vanish from the unit list) is recorded instead of
  stopping; the default stays strict. Live it led into the stage's defeat sequence, so a scene after a loss always stops
  (`scene_after_loss`) and a falling turn counter stops as `stage_restart`.
- Story scenes: the map state is unreadable during dialogue on a zoomed view; Circle advances them, at most 60 in a row
  (`scene_too_long`); whole phase 300 Circles / 15 min.
- Not done: a memory or screen signal for the Game Over / retry screen (needs a live capture).

## Failure behaviour

Every refusal is a `NavigationRefused` before input; every stop is a result, never an exception (an exception disables the
helper mid-phase). Before confirm: nothing irreversible; the agent may Cross out of the menu. After confirm only Circle is
sent. On any stop the game is left where it is and the report says why; the agent hands over with a screenshot.

## Acceptance criteria

1. Unit tests (red first) with an enemy-phase sim: empty-tile choice, open/confirm gating (not done, stopped, twice, wrong
   context, stale screenshot), Circle-only loop reaching T+1, every stop reason, per-call continue, report content.
2. Navigation tests through `InfoNavigation` and node tool schema tests.
3. Ruff, strict mypy, pytest, node and helper tests pass.
4. One protected live run: M9 loop -> End Turn -> enemy phase -> turn 8 confirmed in memory and on a map screenshot; stop
   there (AGENTS.md backups, graceful close, originals verified).
5. Code review (high) without Critical/Important findings.

## Excluded

Defender choices, Save, story choices, playing turn T+1, multi-turn play, healing/Spirit, checkpoints/retries.
