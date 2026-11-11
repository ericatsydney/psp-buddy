"""Choose one Move + Attack for one ready ally from live read dicts (pure, no I/O).

Inputs are the answers of `read_state`, `read_weapons` (for the acting unit) and optionally
per-target hover hit chances, plus a `Policy` from `parse_policy`.
The result is `{"act": {...}, "expect": {...}}` ready for `ppsspp_act`, or
`{"handover": True, "reason": ...}`. Anything unknown or contradictory is a handover, never a guess.

Rules follow `planner.choose_action`: damaged foes before undamaged, then lowest HP; a cheap weapon
on a foe below `cheap_weapon_below_percent` (not a boss), the strongest weapon on a boss above
`strongest_boss_above_percent`, otherwise the median-power weapon. A unit below
`heal_below_percent` HP is handed over (retreat is not planned here). Damage uses the documented
fallback `hit% x effective power` (docs/research/2026-10-21-damage-model.md), for reporting only.
The tile is the nearest reachable one (current tile first) from which the chosen weapon reaches the
target; after a move only weapons with the P flag count, and the weapon must still be
affordable after the move's EN cost (assumed 1 EN per move-cost point, from the 21 Oct live move).
`exclude` lists weapon slots the caller found unusable in game (greyed out).
Boss identity is supplied by the caller (`boss_objects` derives it from names and max HP); with
`non_boss_first` (user rule, 23 Oct) every non-boss foe is tried before any boss. Pilot will is
not decoded: weapons needing more than `will` (default 100) are skipped (22 Oct live: Strike
Freedom Super Dragoon needs 140).

M16 ally safety (user, 3 Nov; docs/superpowers/specs/2026-11-03-ally-safety-advance-design.md):
with `hold_unspirited_turn_one`, a pilot that has not learned Focus or Sense (`spirited`) attacks on
game turn 1 only from its own tile and is otherwise held (`held_turn_one`); an unknown turn counts
as turn 1. With `advance_when_no_target`, a unit that is not held and reaches no foe even after a
move moves to the reachable free tile nearest to the nearest living foe (then lower move cost,
then lower tile), if that is closer than where it stands: an `act` with `move_to` and no `attack`.
With `max_foes_in_reach` N (user, 3 Nov) no move, to attack or to advance, ends on a tile that more
than N living foes can reach next enemy phase: `foe_reach` maps a foe to its move plus longest
weapon range (Manhattan, terrain ignored); a foe missing from it counts as reaching every tile.
Attacking from the unit's own tile is never limited.

M16 after run m16-i (user, 3 Nov): with `strongest_above_percent` N any foe above N% HP gets the
strongest weapon that reaches it (after the cheap rule). With `retreat_damaged` a unit below
`heal_below_percent` is not handed over `retreat_needed`; whatever the turn-1 hold says, it attacks
only from a tile (its own included) that at most `max_foes_in_reach` foes reach, fewest first, then
nearest; otherwise it moves to the free reachable tile with the fewest foes in reach, then farthest
from the nearest foe, then cheaper, then lower (rule `retreat`), or stays (`retreat_stay`) when no
tile beats its own. Without the move overlay the plan stays `no_target`.

Stop-byte fallback (user, 10 Nov; docs/superpowers/specs/2026-11-10-stop-tile-move-range-design.md):
when the Move window is up but the cost byte stayed empty, `act.stop_range` supplies the tiles.
Their real cost is unknown, so such a unit only advances or retreats; it never attacks after that
move.
"""

from collections.abc import Collection, Mapping, Sequence
from fractions import Fraction
from statistics import median
from typing import Any

from . import act, battle_state, targets
from .models import Policy

ASSUMED_WILL = 100       # pilot will is not decoded; weapons needing more are never chosen
BOSS_NAMES = ("Mercurius", "Vayeate", "Wing Gundam Zero")   # user, 23 Oct (stage 23)
BOSS_HP_FACTOR = 2       # user, 23 Oct: max HP at least twice the foes' median is a boss
SAFE_SPIRITS = ("Focus", "Sense")    # user, 3 Nov: either one; Alert does not count
Tile = tuple[int, int]
Candidate = tuple[dict[str, Any], int]      # weapon, number of tiles tried before it reached


def _handover(reason: str) -> dict[str, object]:
    return {"handover": True, "reason": reason}


class _Unknown(Exception):
    pass


def _int(value: object, what: str) -> int:
    if type(value) is not int:
        raise _Unknown(what)
    return value


def _tile(unit: Mapping[str, object]) -> Tile:
    return _int(unit.get("tile_x"), "tile"), _int(unit.get("tile_y"), "tile")


def _alive(unit: Mapping[str, object]) -> bool:
    hp = unit.get("hp")
    return type(hp) is int and hp > 0


def _reachable(state: Mapping[str, Any], here: Tile) -> dict[Tile, int]:
    """Move-range tiles with their move cost, only when the overlay is centred on this unit."""
    raw = state.get("reachable")
    if not raw:
        grid = state.get("map")
        if isinstance(grid, Mapping) and "cost_rows" in grid:
            raw = [[t["x"], t["y"], t["cost"]]
                   for t in battle_state.reachable_tiles({"cost_rows": grid["cost_rows"]})]
    if not raw:
        return {}
    rows = [[int(x), int(y), int(c)] for x, y, c in raw]
    if not act.centered(list(here), rows):
        return {}
    return {(x, y): c for x, y, c in rows}


def _certain_rows(rows: Sequence[Mapping[str, Any]], en: int) -> set[int]:
    """Slots whose attack-menu row is known (`act.menu_row`); MAP weapons are never chosen."""
    return {row["slot"] for row in rows if not (row.get("flags") or {}).get("map")
            and act.menu_row(rows, row, en) is not None}


def _distance(a: Tile, b: Tile) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _rule_and_pick(options: Sequence[dict[str, Any]], target: Mapping[str, Any],
                   policy: Policy, boss: bool) -> tuple[str, dict[str, Any]]:
    hp, max_hp = target["hp"], target["max_hp"]
    if not boss and hp * 100 < policy.cheap_weapon_below_percent * max_hp:
        return "cheap", min(options, key=lambda w: (w["en_cost"] or 0, -w["power"], w["slot"]))
    above = policy.strongest_above_percent
    if (above is not None and hp * 100 > above * max_hp) or (
            boss and hp * 100 > policy.strongest_boss_above_percent * max_hp):
        return "strongest", min(options, key=lambda w: (-w["power"], w["slot"]))
    ranked = sorted(options, key=lambda w: (w["power"], w["slot"]))
    return "median", ranked[(len(ranked) - 1) // 2]


def name_key(name: str) -> str:
    return "".join(ch for ch in name.casefold() if ch.isalnum())


def spirited(pilot: Mapping[str, Any]) -> bool:
    """The pilot (a `spirits.decode_pilot` answer) has learned Focus or Sense."""
    rows = pilot.get("spirits")
    return isinstance(rows, list) and any(
        isinstance(r, Mapping) and r.get("name") in SAFE_SPIRITS and r.get("learned") is True
        for r in rows)


def foe_reach_of(weapon_read: Mapping[str, Any]) -> int | None:
    """Move plus the longest range a foe can use after moving (P weapons), or the longest range
    without moving, whichever is larger; MAP weapons are ignored. None when move is unreadable."""
    move = weapon_read.get("move")
    if type(move) is not int:
        return None
    best = move
    for w in weapon_read.get("weapons") or []:
        flags = w.get("flags") or {}
        top = w.get("max_range")
        if flags.get("map") or type(top) is not int:
            continue
        best = max(best, move + top if flags.get("p") else top)
    return best


def _threats(tile: Tile, foes: Sequence[Mapping[str, Any]], reach: Mapping[int, int]) -> int:
    """Living foes that can reach `tile` next enemy phase (unknown reach: every tile)."""
    return sum(1 for f in foes
               if f["object"] not in reach or _distance(tile, _tile(f)) <= reach[f["object"]])


def _advance(here: Tile, costs: Mapping[Tile, int], occupied: Collection[Tile],
             foes: Sequence[Mapping[str, Any]], unit_object: int) -> dict[str, object]:
    """Move-only plan toward the nearest living foe, or `no_target` when no tile is closer."""
    def nearest(tile: Tile) -> tuple[int, int]:
        return min((_distance(tile, _tile(f)), f["object"]) for f in foes)

    if not foes:
        return _handover("no_target")
    best = min(((nearest(t), costs[t], t) for t in costs if t != here and t not in occupied),
               default=None)
    if best is None or best[0][0] >= nearest(here)[0]:
        return _handover("no_target")
    (distance, foe), _, tile = best
    return {"act": {"unit_object": unit_object, "move_to": list(tile)},
            "expect": {"rule": "advance", "toward": foe, "distance": distance}}


def _retreat(here: Tile, costs: Mapping[Tile, int], occupied: Collection[Tile],
             foes: Sequence[Mapping[str, Any]], reach: Mapping[int, int],
             unit_object: int) -> dict[str, object]:
    """Move-only plan to the tile fewest foes reach, then farthest from the nearest foe."""
    def danger(tile: Tile) -> tuple[int, int]:
        nearest = min((_distance(tile, _tile(f)) for f in foes), default=0)
        return _threats(tile, foes, reach), -nearest

    if not costs:
        return _handover("no_target")           # plan_act opens the move overlay once
    best = min(((danger(t), costs[t], t) for t in costs if t != here and t not in occupied),
               default=None)
    if best is None or best[0] >= danger(here):
        return _handover("retreat_stay")
    (threats, away), _, tile = best
    return {"act": {"unit_object": unit_object, "move_to": list(tile)},
            "expect": {"rule": "retreat", "threats": threats, "distance": -away}}


def _sourced(plan: dict[str, object], stop_byte: bool) -> dict[str, object]:
    """Mark a move built from the stop-byte range, so reports show which units used it."""
    expect = plan.get("expect")
    return ({**plan, "expect": {**expect, "range_source": "stop_byte"}}
            if stop_byte and isinstance(expect, dict) else plan)


def boss_objects(units: Sequence[Mapping[str, Any]], mech_names: Mapping[int, str],
                 names: Collection[str] = BOSS_NAMES,
                 factor: float = BOSS_HP_FACTOR) -> frozenset[int]:
    """Living foes named in `names` (spaces, punctuation and case ignored) or whose max HP is at
    least `factor` x the median max HP of the living foes (`factor` 0 turns the HP rule off)."""
    foes = [u for u in units if targets.is_foe(u.get("raw_menu_group_byte")) and _alive(u)
            and type(u.get("max_hp")) is int]
    if not foes:
        return frozenset()
    wanted = {name_key(n) for n in names}
    middle = median(u["max_hp"] for u in foes)
    return frozenset(u["object"] for u in foes
                     if name_key(mech_names.get(u["object"], "")) in wanted - {""}
                     or (factor and u["max_hp"] >= factor * middle))


def _plan(state: Mapping[str, Any], weapon_read: Mapping[str, Any], policy: Policy,
          unit_object: int, hits: Mapping[int, int],
          bosses: Collection[int], will: int, exclude: Collection[int],
          turn: int | None, is_spirited: bool,
          foe_reach: Mapping[int, int] | None) -> dict[str, object]:
    units = state.get("units")
    if not isinstance(units, list):
        raise _Unknown("state_units")
    mine = [u for u in units if u.get("object") == unit_object]
    if len(mine) != 1:
        raise _Unknown("unit_not_found")
    me = mine[0]
    hp, max_hp = _int(me.get("hp"), "unit_hp"), _int(me.get("max_hp"), "unit_max_hp")
    if me.get("raw_menu_group_byte") != act.ALLY_GROUP or hp <= 0:
        return _handover("unit_not_ally")
    _int(me.get("en"), "unit_en")
    if max_hp <= 0:
        raise _Unknown("unit_max_hp")
    if not me.get("counted_as_unmoved"):
        return _handover("unit_not_ready")
    damaged = hp * 100 < policy.heal_below_percent * max_hp
    if damaged and not policy.retreat_damaged:
        return _handover("retreat_needed")
    rows = weapon_read.get("weapons")
    if weapon_read.get("object") != unit_object or not isinstance(rows, list) or not rows:
        raise _Unknown("weapons")
    by_slot: dict[int, dict[str, Any]] = {}
    for row in rows:
        if (not isinstance(row, Mapping) or type(row.get("slot")) is not int
                or type(row.get("power")) is not int or not isinstance(row.get("name"), str)):
            raise _Unknown("weapon_row")
        if type(row.get("will", 0)) is not int:
            raise _Unknown("weapon_will")
        if row.get("will", 0) <= will and row["slot"] not in exclude:
            by_slot[row["slot"]] = dict(row)
    here = _tile(me)
    foes = [u for u in units if targets.is_foe(u.get("raw_menu_group_byte")) and _alive(u)]
    for foe in foes:
        _tile(foe)
        if _int(foe.get("max_hp"), "foe_max_hp") <= 0:
            raise _Unknown("foe_max_hp")
    occupied = {_tile(u) for u in units if _alive(u) and u.get("object") != unit_object}
    every = _reachable(state, here)
    stop_byte = not every       # user, 10 Nov: the fallback range only ever moves a unit
    if stop_byte:
        every = {(x, y): c for x, y, c in act.stop_range(here, state, weapon_read.get("move"))}
    known = foe_reach or {}
    limit = policy.max_foes_in_reach
    costs = every if limit is None else {
        t: c for t, c in every.items() if _threats(t, foes, known) <= limit}
    held = (policy.hold_unspirited_turn_one and not is_spirited and not damaged
            and (turn is None or turn <= 1))
    moves = sorted((t for t in costs if t != here and t not in occupied and not held
                    and not stop_byte),
                   key=lambda t: (_distance(here, t), t))
    steps: list[tuple[Tile, bool]] = [(here, False), *((t, True) for t in moves)]
    if damaged:     # its own tile is limited too, and the safest attack tile comes first
        steps = sorted((s for s in steps
                        if limit is None or _threats(s[0], foes, known) <= limit),
                       key=lambda s: (_threats(s[0], foes, known), _distance(here, s[0]), s[0]))

    # reach[(tile index)] -> slot -> target objects the weapon can hit from that tile
    reach: list[dict[int, set[int]]] = []
    for tile, moved in steps:
        # A move spends EN (1 per cost point on 21 Oct: (19,5)->(19,6) cost 1, EN 230->229), so
        # the weapon must still be affordable afterwards.
        spent = costs[tile] if moved else 0
        planned = dict(me, tile_x=tile[0], tile_y=tile[1], en=me["en"] - spent)
        try:
            answer = targets.targets_in_range(
                planned, [planned, *(u for u in units if u.get("object") != unit_object)],
                weapon_read, moved=moved)
        except ValueError as exc:
            raise _Unknown("targets") from exc
        per: dict[int, set[int]] = {}
        entries: list[Mapping[str, Any]] = answer["weapons"]  # type: ignore[assignment]
        sure = _certain_rows(rows, planned["en"])
        for entry in entries:
            if entry["usable"] and entry["targets"] and entry["slot"] in sure:
                per[entry["slot"]] = {t["object"] for t in entry["targets"]}
        reach.append(per)

    def order(foe: Mapping[str, Any]) -> tuple[bool, bool, Fraction, int, int]:
        fraction = Fraction(foe["hp"], foe["max_hp"])
        boss_later = policy.non_boss_first and foe["object"] in bosses
        return (boss_later, fraction >= 1, fraction, _distance(here, _tile(foe)), foe["object"])

    # (step index, foe, rule, weapon): the first foe in order, or for a damaged unit the foe it can
    # attack from the safest tile (steps are sorted by danger), then the first in order.
    choice: tuple[int, Mapping[str, Any], str, dict[str, Any]] | None = None
    for foe in sorted(foes, key=order):
        if hits.get(foe["object"]) == 0:
            continue
        options = [by_slot[slot] for slot in {s for per in reach for s in per
                                              if foe["object"] in per[s]}
                   if slot in by_slot]
        if not options:
            continue
        rule, weapon = _rule_and_pick(options, foe, policy, foe["object"] in bosses)
        index = next(i for i, per in enumerate(reach) if foe["object"] in per.get(weapon["slot"],
                                                                                     ()))
        if choice is None or index < choice[0]:
            choice = (index, foe, rule, weapon)
        if not damaged:
            break
    if choice is not None:
        index, foe, rule, weapon = choice
        attack = {"weapon": weapon["name"], "slot": weapon["slot"], "target_object": foe["object"]}
        instruction: dict[str, object] = {"unit_object": unit_object}
        tile, moved = steps[index]
        if moved:
            instruction["move_to"] = list(tile)
        instruction["attack"] = attack
        hit = hits.get(foe["object"])
        expect: dict[str, object] = {
            "hit": hit, "power": weapon["power"], "damage_model": "power", "rule": rule,
            "expected_damage": None if hit is None else hit / 100 * weapon["power"],
            "target_hp": foe["hp"]}
        return {"act": instruction, "expect": expect}
    if damaged:
        return _sourced(_retreat(here, every, occupied, foes, known, unit_object), stop_byte)
    if held:
        return _handover("held_turn_one")
    if policy.advance_when_no_target:
        return _sourced(_advance(here, costs, occupied, foes, unit_object), stop_byte)
    return _handover("no_target")


def plan_attack(state: Mapping[str, Any], weapon_read: Mapping[str, Any], policy: Policy,
                unit_object: int, *, hits: Mapping[int, int] | None = None,
                will: int = ASSUMED_WILL, exclude: Collection[int] = (),
                bosses: Collection[int] = frozenset(), turn: int | None = None,
                spirited: bool = False,
                foe_reach: Mapping[int, int] | None = None) -> dict[str, object]:
    """One act instruction (or handover) for `unit_object`; see the module docstring."""
    try:
        return _plan(state, weapon_read, policy, unit_object, hits or {}, bosses, will, exclude,
                     turn, spirited, foe_reach)
    except (_Unknown, KeyError, TypeError, ValueError) as exc:
        return _handover(f"unknown_{exc}")
