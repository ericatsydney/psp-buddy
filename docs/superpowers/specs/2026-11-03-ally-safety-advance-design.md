# M16 ally safety: turn-1 hold and advance toward foes — design

Approved 3 Nov 2026 (user, via the coordinating session; all four defaults accepted).

## Problem

Run na-b (1 Nov, `m15-s33-noanim`, turn 1, 32 foes starting far away): the runner moved every unit
that could reach a foe; Lockon (GN-SR2, 4800 HP) advanced to attack and was destroyed in the enemy
phase (`ally_destroyed`). Units that could reach nothing stayed put (`no_target`), so the few that
advanced faced the swarm alone.

## Reuse check

- Pilot spirit lists are already decoded (`spirits.decode_pilot`, `learned` per spirit; read through
  `io.spirits(unit)`), verified live 23-25 Oct.
- A move without an attack is already supported (`act.run_act` with `move_to` and no `attack`
  finishes in phase `moved`), and post-move Standby is proven live (`plan_act._standby`, m14s33g).
- The move-range overlay read (`plan_act._open_move_range`) already runs once when nothing is in
  reach. No external tool or library models SRW unit safety; nothing else to reuse.

Approaches compared on 3 Nov: (A) a foe danger map per tile, (B) a turn-1 hold, (C) an HP threshold.
The user chose their own rules (below), close to B plus an advance rule; the danger map is not built.

## Rules (user's words, 3 Nov)

"with focus and sense go as far as you can, without these spirit move in next turn"; "no matter if
the ally can attack foe, just go as far as they can to reach foe"; "either one is enough, alert is
not included, hold back on first turn only then feel free to move". Defaults accepted:

1. **Spirited pilot**: has *learned* Focus or Sense (`learned` true in the spirit list; current SP
   does not matter; Alert does not count). A pilot whose spirits cannot be read counts as not
   spirited (the safe side).
   Amended 3 Nov after run m16-a (user: "Both fixes"): with `use spirits before attacking` on, the
   turn-1 test also needs Focus or Sense active, or cast successfully right then (before any move);
   a skipped cast (e.g. an unchecked Command menu layout) holds the unit. A unit below
   `heal_below_percent` casts nothing (it hands over `retreat_needed`). Spirit rows for VF-25G,
   VF-25F and Arios 5-entry menus were added from screen-checked recon.
2. **Turn-1 hold**: on game turn 1 (turn counter `state.turn.turn == 1`), a pilot who is not
   spirited may attack only from its current tile; with no foe in reach there it stays unmoved
   (skip reason `held_turn_one`). An unreadable turn counter counts as turn 1. A run starting from a
   mid-stage save (turn > 1) holds nobody.
3. **Attack unchanged**: a unit that can attack this turn attacks as today (nearest attack tile).
4. **Advance**: a unit that is not held and has no foe in reach even after moving moves to the
   reachable, unoccupied tile closest (Manhattan) to the nearest living foe, then Standby. Ties: lower
   move cost, then lower (x, y). It does not move if no reachable tile is closer than where it is
   (skip `no_target`). The move needs the move-range overlay; without it the plan stays `no_target`
   (and `plan_act` opens the overlay once, as today).

Third-force units (not group 12) are not foes and are not advanced toward.

## Policy clauses (opt-in, like M11)

- `hold units without focus or sense on turn 1` -> `Policy.hold_unspirited_turn_one`
- `advance toward foes when none is in reach` -> `Policy.advance_when_no_target`

Both off by default, so existing runs and tests are unchanged. The local runner's policy text adds
both.

## Interfaces

- `tactics.plan_attack(..., turn: int | None = None, spirited: bool = False)`.
  - Held unit: only the current tile is planned; no attack -> `{"handover": True, "reason":
    "held_turn_one"}`.
  - Advance: `{"act": {"unit_object": u, "move_to": [x, y]}, "expect": {"rule": "advance",
    "toward": foe_object, "distance": d}}` (no `attack` key).
- `tactics.spirited(pilot) -> bool` from a `spirits.decode_pilot` answer.
- `plan_act.plan_and_act`: reads the turn from the state and, only when the hold clause is on and
  the turn is 1 or unknown, the pilot once (`io.spirits`; any error -> not spirited). A move-only plan runs `act.run_act` (phase `moved`)
  then `_standby`; result `{"ok": True, "phase": "advanced", "moved": True, "standby": bool,
  "plan": plan}`. A failed move-only act returns `phase: "failed"`; when the unit did move (move
  stage recorded, or an unconfirmed move that left it on another tile) it also tries Standby and
  reports `moved: true`, like the attack path. The
  cursor-budget check counts the walk to the destination.
- `plan_act._standby`: on a one-entry post-move menu (Standby alone, if Attack is not offered)
  Circle without Up. A longer menu still needs row 0 first (a last-row read may be stale). Unverified live: whether the
  post-move menu lists Attack when no foe is in reach.
- `turn.TurnLog`: `held_turn_one` is a skip; `advanced` with Standby confirmed is outcome
  `standby` (reason `advance`); `advanced` without a confirmed Standby is `stop`
  (`advance_standby_failed`).

## Failure behaviour

Any unknown datum still hands over (existing `unknown_*`). The spirit read failing never blocks
play; it only makes the unit not spirited. A Standby that is not confirmed after an advance stops
the turn (the unit moved and a menu may be open), exactly like today's failed post-move Standby.

## Out of scope

Danger maps, HP-based retreat, terrain-aware distances, healing/Repair moves, Alert/Invincible.

## Acceptance criteria

1. With both clauses, on turn 1 a non-spirited unit with no foe in reach from its tile is skipped
   `held_turn_one` with no input; one with a foe in reach attacks without moving.
2. On turn 1 a spirited unit with no foe reachable moves to the closest reachable tile and Standby.
3. On turn >= 2 any unit with no foe reachable advances the same way.
4. A unit that can attack attacks exactly as before (all existing tests unchanged).
5. Clauses absent: behaviour identical to today.
6. pytest, ruff, strict mypy pass. A live re-run of `m15-s33-noanim` (after a fresh verified
   backup) is the follow-up trial; not required for offline completion.

## Amendment 3 Nov (user: check all menus so Sense can be cast; Evade above 30% foe hit)

- Spirit and post-move Standby rows come from each menu slot's u32 entry bitmask (8 bytes before the
  count; rising bit = row; Spirit bit 23, Standby bit 25). Without the reader the per-mech table is used.
  A mask that does not list exactly `count` entries, or lacks the bit, means no press.
- A two-pilot unit's Spirit opens SELECT-PILOT (UI window 0x08E4D090): one Circle picks the first pilot
  (the unit's pilot, whose SP is read) before the list.
- Policy clause `evade when the foe hit rate is above N%` -> `enemy_phase evade_above=N`: on each enemy
  forecast (window 0x08E4C81C) whose hover hit is above N, Down to Move (cursor 0x08E4C898 = 3), Circle,
  Down to Eva. (0x08E4CDB8 = 2), Circle; confirmed when the forecast is back on Start and the hit fell.
  A cursor that does not follow is walked back to Start (default answer); an action menu that does not
  open, or a forecast that does not come back, stops the phase (`reaction_failed`).
- Recon helpers (view-only `menu_recon`; `stop_at_window` + `reaction_move`) exist for further screens.
- Policy clause `end moves within reach of at most N foes` (user, 3 Nov; runner N = 2): no move to attack
  or advance ends on a tile more than N living foes can reach next enemy phase (foe move + longest weapon
  usable after moving, or longest range; Manhattan; unread reach = every tile). Attacking from the own
  tile is never limited. Foe reach is read once per trial, shared with the boss-name read.

## Amendment 3 Nov (run m16-i; user: strongest weapon, damaged allies, Def. at 100%) — approved

Run m16-i reached turn 3: a unit damaged in turn 2 was skipped `retreat_needed` and destroyed; every
100% forecast got Evade, which left the hit at 100% (`confirmed: false`). All three clauses are opt-in.

1. `strongest weapons above N%` -> `Policy.strongest_above_percent` (runner N = 10, with
   `cheap weapons below 10%`): a foe above N% HP gets the strongest weapon that reaches it this turn
   (rule `strongest`), boss or not; the cheap rule is checked first. The tile is still the nearest
   one from which that weapon reaches.
2. `move damaged units away from foes` -> `Policy.retreat_damaged`. A unit below `heal_below_percent`
   is not handed over `retreat_needed`; ignoring the turn-1 hold:
   - it attacks only from a tile (its own included) that at most `max_foes_in_reach` foes reach
     (no limit set: any tile), the tile fewest foes reach first, then the nearest; the existing
     cast before the attack applies;
   - otherwise (move overlay read) it moves to the free reachable tile with the fewest foes in
     reach, then farthest from the nearest foe, then lower cost, then lower tile, and Standby
     (rule `retreat`, phase `advanced`); Focus/Sense is cast first under `use spirits before
     attacking`. The destination is not limited by `max_foes_in_reach`.
   - when no tile beats its own (fewer foes, or as many and farther), it casts Focus/Sense the same
     way and stays (skip `retreat_stay`).
   Without the overlay the plan stays `no_target` (the overlay is opened once, as today).
3. `defend when the foe hit rate is at least N%` -> `enemy_phase defend_at=N` (runner N = 100): a
   forecast hit >= N gets Move (row 3), Circle, Def. (SELECT-ACTION row 1), Circle; confirmed when the
   action cursor reached Def. and the forecast is back on Start (Def. does not lower the hit). Below N
   the Evade rule applies unchanged. Failures behave like Evade's.

Review 3 Nov (fixed): a retreat move is checked against the cursor budget before the cast; a damaged
unit picks, over all foes, the attack from the safest (then nearest) tile; foe reach is read when only
the retreat clause is set. Accepted: Def. is confirmed by reaching its row (the hit does not change);
a damaged unit with no time for the overlay read casts nothing; a foe at exactly N% HP gets the median
weapon. Run m16-j: the runner policy (402 characters) exceeded the 400 limit; plan_act and the MCP
now accept up to 800.
