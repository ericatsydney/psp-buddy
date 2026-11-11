# Move range from the "can stop here" byte — design

Date: 10 Nov 2026. Status: design approved by the user 10 Nov ("Yes, write specs"); conflict
review pending.

## Problem

Some ready units are skipped as `no_target` although they could move. In runs s2k-s2m the game
drew a normal Move range for them (screenshot of Deathscythe Hell), but the runner's read found
nothing: cost byte 12 of every map cell stayed zero, `act.centered` refused the range with
`empty`, and `tactics` then had no tiles to choose from. 8 skips in s2k, 4 in s2l, 3 in s2m:
Hyaku Shiki, Methuss, Tower, Gurren Lagann, Deathscythe Hell, Altron, Li-Brasta.

Evidence from the s2m raw-cell dump (3 rejected, 4 accepted units, one open map):

| Unit | Result | Byte 2 tiles | Cost tiles | Byte 2 and not cost | Furthest byte 2 tile | Own tile marked |
|---|---|---|---|---|---|---|
| Altron Gundam | rejected | 101 | 0 | 101 | 7 | no |
| Deathscythe Hell | rejected | 99 | 0 | 99 | 7 | no |
| Hyaku Shiki | rejected | 90 | 0 | 90 | 7 | no |
| Destiny Gundam | accepted | 92 | 112 | 0 | 7 | no |
| Gundam DX G Falcon | accepted | 126 | 144 | 0 | 8 | no |
| Infinity Justice G | accepted | 94 | 112 | 0 | 7 | no |
| Zangetsu | accepted | 98 | 112 | 0 | 7 | no |

Byte 2 marks the tiles a unit can stop on; on accepted units it is always a subset of the costed
tiles, and the cost-only tiles are those it can pass but not stop on. Why byte 12 is empty for
some units is unknown (Move-window words +0x30, +0x34, +0x40 are 1 on rejected units and 0 on
accepted ones; meaning unknown). The fix does not depend on that answer.

Skips from running out of the 400 cursor presses (s2k, turn 3) are a separate cause and are not
changed here.

## Reuse check

No API, MCP server, plugin or library offers this. `mcp-ppsspp` (assessed 14 Oct) reads memory but
knows nothing of this game's map cells. One web search for a ULJS00460 memory map found only money
and upgrade cheat codes. The project's own `decode_map`, `act.centered` and `plan_attack` are
extended instead.

## Approaches

1. Byte 2 tiles, distance as the assumed cost, normal move and attack. Rejected in the conflict
   review (D2): it would guess a move cost for a weapon decision.
2. **Byte 2 tiles, move only, no attack after that move (chosen, D2).** Advance and retreat work;
   no EN or weapon decision depends on the unknown cost. Those units lose an attack that needs a
   move; an attack from their own tile is unaffected, since that is planned without a Move range.
3. Investigate why byte 12 is empty. More live runs, no guaranteed answer, and unnecessary for
   choosing a destination.

## Scope

In: the fallback range for move-only planning (advance, retreat) and for the Move stage; honest reporting when neither byte
gives a range; report fields proving which units used it.

Out: the cause of the empty byte 12; the 400-press budget; the post-attack move prompt; the
view-only `_probe_move`; `s2j` `result_not_dismissed`; free-form terrain cost modelling.

## Design

`battle_state.decode_map` also returns `stop_rows`, one string per map row from cell byte 2 (same
`_symbol` encoding as `cost_rows`). `battle_state.stop_tiles(map)` returns the marked `(x, y)`.

`act.stop_range(tile, state, move) -> list[list[int]]` is the only way to get fallback tiles.
It returns `[x, y, distance]` rows, or `[]` unless every check passes:

- the cost rows are empty (`_reachable(state)` has no tiles);
- `state["screen"] == "move_range"` (the UI window pool shows this unit's Move window is up);
- `move` is an int of at least 1;
- at least one tile is marked, the unit's own tile is not, and every marked tile is within
  `move` tiles of it (Manhattan distance).

The distance fills the cost slot for tie-breaks only (a lower bound on the real cost); nothing
that spends EN or picks a weapon reads it.

`cost_rows` remain the first choice everywhere. Only two callers gain the fallback:

- `tactics._reachable(state, here, move)`: when the cost rows are empty, uses
  `act.stop_range(here, state, weapon_read["move"])`, and reports that the range is the fallback.
  With the fallback, `_plan` adds no move steps for attacking: only the own-tile attack, advance
  and retreat remain. The 2-foe rule, turn-1 hold and retreat rules apply unchanged. A plan built
  from these tiles adds `"range_source": "stop_byte"` to `expect`.
- `act` Move stage: after `range_when_drawn` still finds no costed range, and only when the
  instruction has no `attack`, it reads the unit's `move` with `io.read_weapons` and uses
  `stop_range`. An instruction with an attack keeps today's `range_not_centered_on_unit`.
  Destination membership is checked against whichever range was accepted; the stage record gains
  `range_source`.

`range_when_drawn` still polls its full 7 reads for a costed range before any fallback, so a slow
draw of a normal range can never be mistaken for this case. Cost: up to about 1.8 s more per read
for an affected unit, which is what these units already spend today.

`_post_attack_move`, `_probe_move` and `act.centered` stay cost-only, so a leftover byte 2 can never
look like a post-attack move prompt.

`plan_act._plan_and_act`: if the plan after opening the Move overlay is still `no_target` and the
overlay state gave neither costed tiles nor a valid `stop_range`, the reason becomes
`move_range_unreadable`, added to `turn.SKIP_HANDOVERS`. `rejected-ranges.jsonl` stays, and gains
`stop_tiles` (count) and `stop_range_valid`.

## Data flow

Select unit -> Move -> `range_when_drawn` -> planner picks a tile from costs, else byte 2 ->
menus close -> `act` reopens Move -> same range check -> cursor walks -> existing destination,
`move_not_confirmed` and Standby checks.

## Failure behaviour

| Case | Result |
|---|---|
| Byte 2 stale from another unit, or the Move window not up | `stop_range` returns `[]`; unit skipped, `move_range_unreadable` |
| Move stat unreadable, or lower than a marked tile's distance | same |
| Destination not valid at the Move stage | existing `destination_not_reachable`, backs out |
| Game refuses the tile (unit still on its start tile) | unchanged `move_not_confirmed`: the run stops with the Move window open, kept on purpose for diagnosis (D1) |
| Costed range at planning, none at the Move stage, with an attack planned | existing `range_not_centered_on_unit`, backs out |

## Acceptance criteria

1. Costed ranges behave exactly as before: every existing test passes unchanged, apart from
   expected-value updates for the new `stop_rows` key.
2. Unit tests: `decode_map` returns `stop_rows`; `stop_range` accepts the s2m shape and refuses each
   failure in the table; the planner advances and retreats from fallback tiles, never plans an
   attack after a fallback move, and still attacks from the own tile; `act.move` accepts a fallback
   destination for a move-only instruction, refuses one outside it and refuses the fallback when
   an attack is planned; `_post_attack_move` ignores byte 2; both empty reports
   `move_range_unreadable`.
3. Replay of the logged s2l/s2k state where possible gives an advance instead of `no_target`.
4. `pytest --basetemp local/pytest-stop` (all pass), local tool tests, `ruff`, strict `mypy` pass.
5. Live, on a protected run: at least one previously skipped unit moves using `range_source:
   stop_byte`, landing on the planned tile; no ally lost to a wrong move; originals unchanged.
   Afterwards a run on a map with rough terrain, since byte 2 has only been seen on an open map.

## Conflict review

`/plan-eng-review`, 10 Nov, read-only, against `docs/features.md`, the open items in
`docs/progress.md`, the touched code and tests, and the AGENTS.md save rules. Decisions by the user:

- **D1, refused tile** (`act.py:373`, `turn.py:116`; features.md:60 "never with a menu open"):
  keep today's behaviour. A refused fallback tile stops the run with the Move window open.
  features.md:60 stays true for failed attacks and moves that land elsewhere; a refused move is a
  known exception to record there.
- **D2, assumed cost** (`tactics.py:6` "never a guess"): move only. No attack after a fallback
  move, so the planner rule stands without an exception. This replaces the distance-as-cost
  choice approved earlier the same day.
- **D3, cursor budget** (features.md:74, 31 Oct): keep 400 presses per turn. Units that now move
  can reach the limit sooner; the live run measures it.

No conflict found with: 2-foe rule, foe reach, advance, retreat, turn-1 hold, boss rules, start-up
back-out, enemy-phase reactions, the rejected-range diagnostic, or save protection (no change to
backup or launch steps). Open items s2j, debugger freeze: unrelated. The s2k/s2l/s2m open item
closes when acceptance criterion 5 passes. Outside review was not run, since it would send project
content to an external provider.
