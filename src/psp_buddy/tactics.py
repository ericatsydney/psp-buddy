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
Boss identity is supplied by the caller.
"""

from collections.abc import Collection, Mapping, Sequence
from fractions import Fraction
from typing import Any

from . import act, battle_state, targets
from .models import Policy

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


def _distance(a: Tile, b: Tile) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _rule_and_pick(options: Sequence[dict[str, Any]], target: Mapping[str, Any],
                   policy: Policy, boss: bool) -> tuple[str, dict[str, Any]]:
    hp, max_hp = target["hp"], target["max_hp"]
    if not boss and hp * 100 < policy.cheap_weapon_below_percent * max_hp:
        return "cheap", min(options, key=lambda w: (w["en_cost"] or 0, -w["power"], w["slot"]))
    if boss and hp * 100 > policy.strongest_boss_above_percent * max_hp:
        return "strongest", min(options, key=lambda w: (-w["power"], w["slot"]))
    ranked = sorted(options, key=lambda w: (w["power"], w["slot"]))
    return "median", ranked[(len(ranked) - 1) // 2]


def _plan(state: Mapping[str, Any], weapon_read: Mapping[str, Any], policy: Policy,
          unit_object: int, hits: Mapping[int, int],
          bosses: Collection[int]) -> dict[str, object]:
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
    if hp * 100 < policy.heal_below_percent * max_hp:
        return _handover("retreat_needed")
    rows = weapon_read.get("weapons")
    if weapon_read.get("object") != unit_object or not isinstance(rows, list) or not rows:
        raise _Unknown("weapons")
    by_slot: dict[int, dict[str, Any]] = {}
    for row in rows:
        if (not isinstance(row, Mapping) or type(row.get("slot")) is not int
                or type(row.get("power")) is not int or not isinstance(row.get("name"), str)):
            raise _Unknown("weapon_row")
        by_slot[row["slot"]] = dict(row)
    here = _tile(me)
    foes = [u for u in units if u.get("raw_menu_group_byte") == targets.ENEMY_GROUP and _alive(u)]
    for foe in foes:
        _tile(foe)
        if _int(foe.get("max_hp"), "foe_max_hp") <= 0:
            raise _Unknown("foe_max_hp")
    occupied = {_tile(u) for u in units if _alive(u) and u.get("object") != unit_object}
    costs = _reachable(state, here)
    steps: list[tuple[Tile, bool]] = [(here, False)]
    moves = sorted((t for t in costs if t != here and t not in occupied),
                   key=lambda t: (_distance(here, t), t))
    steps += [(t, True) for t in moves]

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
        for entry in entries:
            if entry["usable"] and entry["targets"]:
                per[entry["slot"]] = {t["object"] for t in entry["targets"]}
        reach.append(per)

    def order(foe: Mapping[str, Any]) -> tuple[bool, Fraction, int, int]:
        fraction = Fraction(foe["hp"], foe["max_hp"])
        return (fraction >= 1, fraction, _distance(here, _tile(foe)), foe["object"])

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
        attack = {"weapon": weapon["name"], "slot": weapon["slot"], "target_object": foe["object"]}
        instruction: dict[str, object] = {"unit_object": unit_object}
        if index:
            instruction["move_to"] = list(steps[index][0])
        instruction["attack"] = attack
        hit = hits.get(foe["object"])
        expect: dict[str, object] = {
            "hit": hit, "power": weapon["power"], "damage_model": "power", "rule": rule,
            "expected_damage": None if hit is None else hit / 100 * weapon["power"],
            "target_hp": foe["hp"]}
        return {"act": instruction, "expect": expect}
    return _handover("no_target")


def plan_attack(state: Mapping[str, Any], weapon_read: Mapping[str, Any], policy: Policy,
                unit_object: int, *, hits: Mapping[int, int] | None = None,
                bosses: Collection[int] = frozenset()) -> dict[str, object]:
    """One act instruction (or handover) for `unit_object`; see the module docstring."""
    try:
        return _plan(state, weapon_read, policy, unit_object, hits or {}, bosses)
    except (_Unknown, KeyError, TypeError, ValueError) as exc:
        return _handover(f"unknown_{exc}")
