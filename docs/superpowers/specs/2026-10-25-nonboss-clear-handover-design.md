# M13 — Clear the non-boss foes, then hand over (design)

Date: 25 Oct 2026. Status: approved by the user on 25 Oct (approach A, 5-turn budget).

## Goal

From a turn-start state (first `local/checkpoints/turn7-start`, stage 23, turn 7), the auto-runner plays
player turns, End Turn and enemy phases until no living non-boss foe is left. Then it stops on the map
and hands control back to the player, who fights the bosses (user, 25 Oct: "Clear the map for non-boss
robot, then handover back to the player to continue").

## User decisions (25 Oct)

| Question | Decision |
|---|---|
| When is "cleared" checked? | After every unit's action and after every enemy phase. Stop as soon as no non-boss foe is left, even mid-turn; the remaining allies stay unmoved for the player. |
| Ally lost before the clear? | Stop and hand over at once (strict mode). No retry, no reload. The player decides. |
| Handover state | PPSSPP open on the map, no menu open, plus a JSON report. No savestate. |
| Boss targets while non-bosses remain | Keep today's order: non-bosses first; a unit with only a boss in reach attacks it with its strongest weapon (policy `strongest boss weapons above 0%`). |
| Approach | A: the clear check is a field in `turn_next`. |
| Turn budget | 5 player turns (turn 7 to 11 from the checkpoint), then hand over. |

## Reuse check

There is no external API, MCP server, plugin or library for SRW Z2 tactics. This milestone reuses the project's own
modules: `tactics.boss_objects` / `BOSS_NAMES`, `turn.next_unit` / `TurnLog`, `plan_act`, `end_turn`
(`open_menu`, `confirm`, `advance` with `accept_losses=False`), `retry.lost_allies`, the drivers
`local/m12-tools/m12_loop.py` and `local/m10-tools/end_turn_steps.py`, and the M12 checkpoint
`local/checkpoints/turn7-start` (manifest checked with `retry.mismatches`). The checkpoint retry
(`retry.Ledger`) is not used here (user: no retry focus).

Evidence from run m12try1 (25 Oct, same checkpoint): turn 7 ran out of non-boss targets during the
player turn (7 units skipped `no_target`). Later shots went into bosses, and Wing Gundam Zero then cut
Gundam 00 to 364 HP in the enemy phase. With the stop rule, this run would have handed over mid-turn 7.

## Scope

In:
- `src/psp_buddy/clear.py` (new, pure): the boss set fixed at the start, the non-boss check, ally-loss check,
  the handover decision and the handover report.
- `turn_next` gains a `clear` field and a `handover` answer. It is still memory-only and sends no input.
- Multi-turn play in one helper session: after an enemy phase ends `done` (turn T+1 seen, allies reset),
  the helper starts a new player turn. Today it refuses all input after the first End Turn.
- `handover.json` in the run's evidence folder. Once a handover is decided, the helper refuses all further input.
- Driver `local/m13-tools/clear_loop.py` (ignored folder, like the M9-M12 drivers).

Out: retries/reloads, savestates at handover, boss-specific tactics, new spirits or commands, stages
other than the checkpoint's (the design is general, but only stage 23 is tested), speed work.

## Definitions

- **Foe**: a unit with `raw_menu_group_byte == targets.ENEMY_GROUP` (12). Third-force units (group 4,
  e.g. Wing Gundam Zero at turn 7, HIT 0%) are not foes for the clear check, and they are never counted.
- **Boss set** (fixed): computed once, at the first `turn_next` of the helper session, as
  `tactics.boss_objects(units, mech_names)` (names `BOSS_NAMES`, or max HP ≥ 2× the median max HP of living
  foes). Foe mech names are read with the existing memory-only weapon read into the shared
  `_mech_names` cache, the same way as `plan_act._bosses`. The set is never recomputed. Once only bosses are
  left, the median would equal their own HP, and the HP rule would stop marking them as bosses.
  A foe that appears later (reinforcements) is boss only by name. Turn 7: Mercurius and Vayeate.
- **Non-boss left**: living foes (HP > 0 and still in the unit list) not in the boss set. Destroyed units
  vanish from the list in live play (M10). Both cases count as gone.
- **Ally lost**: `retry.lost_allies(start_state, state)` is non-empty, where `start_state` is the state at
  the first `turn_next` (allies gone from the list or at 0 HP).

## Interfaces

### `clear.py`

```python
TURN_BUDGET = 5

@dataclass(frozen=True)
class ClearRun:
    start_turn: int
    bosses: frozenset[int]
    start: Mapping[str, Any]          # first state, for ally-loss checks and the report

def begin(state, mech_names, names=BOSS_NAMES) -> ClearRun
def nonboss_left(run: ClearRun, state) -> list[int]          # sorted objects
def decide(run: ClearRun, state, *, budget=TURN_BUDGET) -> str | None
    # "ally_lost" (checked first) | "cleared" | "turn_budget" (turn > start_turn + budget - 1
    #  at a new player turn) | None = keep playing
def handover_report(run, state, reason, *, mech_names, extra) -> dict
```

`decide` raises `ValueError` on an unreadable state (no unit list, no turn). `turn_next` turns that
into the existing `stopped: unknown_state: ...` answer.

### `turn_next` answer (added fields)

```json
{"clear": {"nonboss_left": [149301208], "bosses": [149302872, 149302976], "turn": 7},
 "handover": null}
```

When `decide` returns a reason, the answer is `done: false`, `unit_object: null` and
`"handover": {"reason": "cleared"}`. The helper writes `handover.json` and sets `_handed_over`. From then on
every input operation (`press`, `goto`, `act`, `plan_act`, `probe_move`, `end_turn`, `enemy_phase`) is
refused. Memory reads and screenshots stay allowed, so the agent can confirm the screen.

### New player turn

When `enemy_phase` returns `phase: "done"`, the helper resets the per-turn state: `_end_phase = None`,
`_end_menu_open = False`, `_turn = TurnLog()`, `_turn_done = False`, `_act_pending = None`. It also resets the
per-turn budgets (`MAX_ACTS`, `MAX_ACT_PRESSES`, `MAX_GOTO_PRESSES`, `MAX_PROBES`, `MAX_HIT_READS`,
`MAX_TARGET_READS`, `MAX_WEAPON_READS`, `MAX_STATE_READS`). Per-trial limits stay per trial: taps, dumps, and a new
`MAX_PLAYER_TURNS = 6` (budget + 1, defence in depth). The finished turn's report is kept as
`turn-report-<turn>.json`, and `turn-report.json` then holds the current turn. An enemy phase that ends `stopped` does
not reset anything: input stays refused as today. The next `turn_next` answers
`handover: {"reason": <stop reason>}`, e.g. `ally_destroyed`, `scene_after_loss`, `stage_restart`.

### `handover.json`

```json
{"reason": "cleared", "turns": [7, 8], "turns_played": 2,
 "bosses": [{"object": 0, "name": "Mercurius", "hp": 0, "max_hp": 0, "tile": [0, 0]}],
 "nonboss_destroyed": [0], "nonboss_left": [],
 "allies": [{"object": 0, "hp": 0, "max_hp": 0, "en": 0, "unmoved": true, "tile": [0, 0]}],
 "lost": [], "turn_reports": ["turn-report-7.json"], "enemy_phase_reports": ["enemy-phase-report-7.json"],
 "screen": null}
```

`screen` is filled in by the driver. It takes a final screenshot after the handover and adds its name and SHA-256
to a copy (`handover-final.json`). The helper's file is never rewritten by the driver.

### Driver `local/m13-tools/clear_loop.py`

Loop: `turn_next` → handover? stop : (unit? screenshot + `plan_act` : turn done? `end_turn open` →
menu screenshot → `end_turn confirm` → `enemy_phase` (strict) until not `continue`) → repeat.
After the handover: one screenshot, write `handover-final.json`, print the summary, end the helper
**without closing PPSSPP**, and leave the game on the map.

## Failure behaviour

- An unreadable state: `turn_next` already reads again on a refusal (driver). After the existing
  stop, the driver reports `stopped:<reason>` as the handover reason and sends no input.
- `plan_act` failure or stop: as today (`TurnLog` skip or stop). A turn stop is a handover with the stop
  reason.
- Ally lost in the player turn (a counter): the next `turn_next` sees it and hands over `ally_lost`.
- Ally lost in the enemy phase: strict `advance` stops `ally_destroyed`, and the helper hands over with that
  reason. The screen may still be in a scene. `handover.json` says so (`screen_state: "after_stop"`),
  and the driver sends no Circle.
- Turn budget reached at a new player turn: `turn_budget` handover before any input in that turn.
- The helper's End Turn and enemy-phase guards are unchanged inside a turn.

## Acceptance criteria

1. `clear.py` unit tests (red first): boss set frozen (a two-boss-left state still has `nonboss_left == []`),
   group 4 ignored, a vanished foe counts as gone, ally lost has priority over cleared, turn budget,
   unreadable state raises.
2. `turn_next` tests: the `clear` field, a handover answer, `handover.json` written, all inputs refused after a
   handover, reads still allowed.
3. Multi-turn tests: after `enemy_phase` `done`, `plan_act` and End Turn are allowed again, and the budgets are reset;
   after `stopped` they are not; `MAX_PLAYER_TURNS` holds; the per-turn report files are kept.
4. Node tool schema: `ppsspp_turn_next` description mentions the handover. Node tests pass.
5. ruff, strict mypy, pytest (with `--basetemp local/...`), helper tests and node tests all pass.
6. Live (a later session, with AGENTS.md backups 54/54 verified before launch, graceful close only at the end, by the
   user): from `turn7-start` (manifest `mismatches == []`), the run ends `cleared` with no ally lost, the game is
   on the map with no menu open, and `handover.json` matches the final screenshot (bosses' HP, allies unmoved).

## Risks and open points

- Helper exit (checked 25 Oct, plan Task 4): the handoff spawns PPSSPP through `NoCloseProcess` and serves
  the mailbox until the PPSSPP process exits (`local/move-attack-trial-20261017/handoff.py`, the serve
  loop). The helper never closes the emulator. After a handover it stays idle with every input refused, until the
  player closes PPSSPP; it then exits by itself. No separate "release" step is needed.
- `plan_act` still recomputes bosses per call with the median rule. On stage 23 both bosses are named, so the
  target order is unaffected. Passing the fixed set to `plan_act` is a small follow-up, not in this scope.
- A second player turn has never been played live: turn 8 with allies reset is new ground (budgets,
  dialogues at the turn start, `scene_at_new_turn`).
