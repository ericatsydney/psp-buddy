# Effective move value — design

Date: 10 Nov 2026. Status: conflict review complete; D1 and D2 decided by the user (10-11 Nov).

## Problem

The stop-byte fallback ([spec](2026-11-10-stop-tile-move-range-design.md)) only accepts tiles within
the unit's move. `weapons.read_unit_weapons` returns the stored move (unit runtime `+0x15`), but the
game adds bonuses when it draws the range. In runs s2n and s2o Hyaku Shiki was refused
`move_range_unreadable`: stored move 6, game range 7, with 12 safe closer tiles available.

Evidence: [effective move research](../../research/2026-11-10-effective-move.md). The game's move
function at `0x0896A090` adds to the stored value, in order:

| Step | Bonus | Status |
|---|---|---|
| Effect flag, pilot runtime `+0x14` mask `0x80` (probably the Accel spirit) | +3 | decoded; not seen live |
| Pilot skill 21, Dash | +1 | decoded; Hyaku Shiki fits |
| Dash at will (`+0x46`) 130 or more, and `0x08861E54(pilot)` true | +2 instead | that call not decoded; the game's own rule is +2 at 130 ([pilot abilities](https://akurasu.net/wiki/Super_Robot_Wars/Z2/Pilot_Abilities)) |
| Table bonus, only when the high nibble of runtime `+0x45` is non-zero | varies | not decoded; 0 on all 68 units in this save |
| General effect engine `0x088E1458` | varies | not decoded |

In the s2o checkpoint skill 21 is held by Hyaku Shiki, VF-25F Messiah and one foe, the boss PearlFang.
No unit has the effect flag.

## Reuse check

No API, MCP server, plugin or library knows this game's move formula (same search as the stop-byte
spec, 10 Nov: `mcp-ppsspp` reads memory only). The project's own `weapons.read_unit_weapons`, which
already reads the pilot's skills, is extended.

## Approaches

1. **`move` becomes the effective value everywhere (recommended).** One meaning of "move" for allies
   and foes. The fallback accepts Hyaku Shiki, and foe reach, which feeds your 2-foe rule, also
   becomes correct. A foe with skill 21 can now count as reaching one tile further.
2. Separate `effective_move` used only by the fallback. Foe reach stays exactly as it is, and keeps
   under-reading foes with skill 21.
3. Allow any tile within stored move + 1 in the fallback. Smallest change, no decoding used, but it
   loosens the check for every unit and is still wrong at +2 or +3.

## Scope

In: the two decoded bonuses in `read_unit_weapons`; report fields showing them; `range_source` in the
turn report, because the stop-byte spec's live acceptance needs a field that today is never written
to a file (only `act`'s stage record holds it, and s2o's evidence has no `stop_byte` entry).

Out: decoding `0x08861E54`, the table bonus and the effect engine; terrain costs; the cause of the
empty cost byte; the post-attack move prompt; the s2o Get Result stop; the debugger freeze.

## Design

`weapons.py` gains `MOVE_SKILL = 21`, `MOVE_SKILL_WILL = 130`, `MOVE_EFFECT_MASK = 0x80`,
`MOVE_EFFECT_BONUS = 3`, and:

`async def _move_bonus(read, pilot, skills) -> int`

- `skills is None` (no readable pilot): 0.
- Reads pilot runtime `+0x14` (u16): `+3` when the `0x80` bit is set.
- With skill 21 at level above 0: reads `+0x46` (s16); `+2` at 130 or more, otherwise `+1`.

`read_unit_weapons` returns `"move"` = stored + bonus, plus `"stored_move"` and `"move_bonus"`.

**Will 130 (D2).** Skill 21 is Dash: +1 move, +2 at will 130 or more (wiki, confirmed by the user, 11
Nov). The code follows that rule. `0x08861E54` stays undecoded; if it ever made the game give +1, `move`
would be one too high, which only loosens a limit: `stop_range` uses it as a ceiling, and foe reach
errs towards caution. Nothing uses `move` as a minimum.

Callers are unchanged: `act.stop_range` (through `act` and `tactics`), `tactics.foe_reach_of`, and the
`move` field in `rejected-ranges.jsonl`. `turn.py` adds `range_source` to a report entry when the plan's
`expect` has one.

## Failure behaviour

| Case | Result |
|---|---|
| Unit gets a bonus we do not decode | Marks beyond `move`; `stop_range` refuses; skipped `move_range_unreadable`, as today |
| Upper bound is 1 too high (undecoded condition false) | Only the limit is looser by 1; tiles still come from the game's own marks |
| Pilot memory unreadable | Existing behaviour: no pilot gives bonus 0; an invalid read still refuses the whole weapon read |
| Foe's will rises after its reach is cached | Reach stays at the first value for that trial (existing per-trial cache), as today for every other field |

## Acceptance criteria

1. Tests: no pilot, no skill, skill 21, skill 21 at 129 and 130, flag alone, flag plus skill; stored
   value reported; `foe_reach_of` uses the effective value; turn entry carries `range_source` only
   when present.
2. Offline, s2o checkpoint: Hyaku Shiki 7, Altron 7, Deathscythe Hell 7, VF-25F Messiah 9, PearlFang 8.
3. Offline, s2o's logged marks: Hyaku Shiki's 90 cells pass `stop_range` with the new value.
4. `pytest --basetemp local/pytest-x` (all pass, no path argument), local tool tests, `ruff`, `mypy`.
5. Live, protected, slot 2 save of 13:27: Hyaku Shiki advances on turn 1 with `range_source: stop_byte`
   in the turn report, landing on the planned tile; originals unchanged.

## Conflict review

`/plan-eng-review`, 10 Nov, read-only, against `docs/features.md`, the open items in
`docs/progress.md`, the touched code and tests, and the AGENTS.md save rules. Report:
`~/.gstack/projects/ericatsydney-psp-buddy/m14-stage33-eng-review-effective-move-20261110.md`.
Outside review not run (it would send project content to an external provider); `gstack-review-log`
unavailable (`bun` missing).

- **D1, foe reach** (`tactics.py:140`; features.md:90-95): decided by the user, 10 Nov: allies and foes
  both use the effective value (Approach 1). PearlFang goes from 7 to 8 in this save.
- **D2, will 130+** (`tactics.py:6` "never a guess"): decided by the user, 11 Nov: skill 21 is Dash,
  +1, and +2 at will 130 or more, as the game documents it. Not a guess, so no exception to the rule.

Corroboration: the [parts list](https://akurasu.net/wiki/Super_Robot_Wars/Z2/Parts) gives no movement
for Hyaku Shiki's parts, and its Movement values match the part records read from memory.

Plan notes from the review: define the pilot effect offset in `weapons.py` and import it in
`spirits.py`; one `_pilot_runtime` helper and one read of `+0x14..+0x48`. The game ORs the whole crew's
effect masks while this reads the main pilot only, so a sub-pilot's +3 is under-read and the unit is
skipped, which is safe. No conflict with save protection.
