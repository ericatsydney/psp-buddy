"""Clear the non-boss foes, then hand over (M13). Pure logic, no emulator access.

User decisions (25 Oct): the runner stops as soon as no living non-boss foe is left (checked after
every action and every enemy phase), stops at once on any ally loss, and gives up after a budget of
player turns. The boss set is fixed at the start: with only bosses left the median-HP rule of
`tactics.boss_objects` would stop marking them, so it is never recomputed. Later foes
(reinforcements) are bosses only by name. Third-force units (group 4) are not foes here.
"""

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Any

from . import retry, targets
from .tactics import BOSS_HP_FACTOR, BOSS_NAMES, boss_objects, name_key

TURN_BUDGET = 5          # user, 25 Oct: player turns 7 to 11 from the turn-7 checkpoint


@dataclass(frozen=True)
class ClearRun:
    start_turn: int
    bosses: frozenset[int]
    start: Mapping[str, Any]      # {"turn", "units": [{"object", "group", "hp", "max_hp", "tile"}]}
    names: frozenset[str]         # boss name keys, for foes that appear later


def _units(state: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    units = state.get("units")
    if not isinstance(units, list) or not units:
        raise ValueError("state has no units")
    keys = ("object", "raw_menu_group_byte", "hp")
    if not all(type(u.get(k)) is int for u in units for k in keys):
        raise ValueError("unit with unreadable fields")
    return units


def _turn(state: Mapping[str, Any]) -> int:
    turn = state.get("turn")
    value = turn.get("turn") if isinstance(turn, Mapping) else None
    if type(value) is not int:
        raise ValueError("turn counter unreadable")
    return value


def _tile(u: Mapping[str, Any]) -> list[int] | None:
    x, y = u.get("tile_x"), u.get("tile_y")
    return [x, y] if type(x) is int and type(y) is int else None


def begin(state: Mapping[str, Any], mech_names: Mapping[int, str],
          names: Collection[str] = BOSS_NAMES, *, factor: float = BOSS_HP_FACTOR) -> ClearRun:
    """The run's fixed boss set and start state, from the first state of the helper session.
    `factor` 0 keeps only the named bosses (a checkpoint that names its stage's bosses)."""
    units, turn = _units(state), _turn(state)
    start = {"turn": turn, "units": [
        {"object": u["object"], "group": u["raw_menu_group_byte"], "hp": u["hp"],
         "max_hp": u.get("max_hp"), "tile": _tile(u)} for u in units]}
    return ClearRun(turn, boss_objects(units, mech_names, names, factor), start,
                    frozenset(name_key(n) for n in names) - {""})


def _is_boss(run: ClearRun, obj: int, mech_names: Mapping[int, str]) -> bool:
    return obj in run.bosses or name_key(mech_names.get(obj, "")) in run.names


def nonboss_left(run: ClearRun, state: Mapping[str, Any],
                 mech_names: Mapping[int, str] | None = None) -> list[int]:
    """Living foes outside the boss set (a destroyed unit vanishes from the list live, M10)."""
    names = {} if mech_names is None else mech_names
    return sorted(u["object"] for u in _units(state)
                  if targets.is_foe(u["raw_menu_group_byte"]) and u["hp"] > 0
                  and not _is_boss(run, u["object"], names))


def decide(run: ClearRun, state: Mapping[str, Any], *, budget: int = TURN_BUDGET,
           mech_names: Mapping[int, str] | None = None) -> str | None:
    """`ally_lost`, `cleared`, `turn_budget` or None (keep playing); ValueError if unreadable."""
    left = nonboss_left(run, state, mech_names)
    turn = _turn(state)
    if retry.lost_allies(run.start, state):
        return "ally_lost"
    if not left:
        return "cleared"
    if turn > run.start_turn + budget - 1:
        return "turn_budget"
    return None


def status(run: ClearRun, state: Mapping[str, Any],
           mech_names: Mapping[int, str] | None = None) -> dict[str, Any]:
    """The `clear` field of a `turn_next` answer."""
    return {"nonboss_left": nonboss_left(run, state, mech_names), "bosses": sorted(run.bosses),
            "turn": _turn(state)}


def handover_report(run: ClearRun, state: Mapping[str, Any], reason: str, *,
                    mech_names: Mapping[int, str],
                    extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The handover summary (spec: handover.json); `screen` is added later by the driver."""
    now = {u["object"]: u for u in _units(state)}
    turn = _turn(state)
    bosses = []
    for s in run.start["units"]:
        if s["object"] in run.bosses:
            u = now.get(s["object"])
            bosses.append({"object": s["object"], "name": mech_names.get(s["object"], ""),
                           "hp": u["hp"] if u else 0, "max_hp": s["max_hp"],
                           "tile": _tile(u) if u else None})
    started = {s["object"] for s in run.start["units"]}
    bosses += [{"object": u["object"], "name": mech_names.get(u["object"], ""), "hp": u["hp"],
                "max_hp": u.get("max_hp"), "tile": _tile(u)}
               for u in now.values() if u["object"] not in started and u["hp"] > 0
               and targets.is_foe(u["raw_menu_group_byte"])
               and _is_boss(run, u["object"], mech_names)]          # late, named bosses
    left = nonboss_left(run, state, mech_names)
    first = [s["object"] for s in run.start["units"]
             if targets.is_foe(s["group"]) and s["hp"] > 0 and s["object"] not in run.bosses]
    allies = [{"object": u["object"], "hp": u["hp"], "max_hp": u.get("max_hp"), "en": u.get("en"),
               "unmoved": u.get("counted_as_unmoved") is True, "tile": _tile(u)}
              for u in now.values() if u["raw_menu_group_byte"] == retry.ALLY_GROUP]
    return {"reason": reason, "turns": [run.start_turn, turn],
            "turns_played": turn - run.start_turn + 1,
            "bosses": bosses, "nonboss_destroyed": sorted(set(first) - set(left)),
            "nonboss_left": left, "allies": allies, "lost": retry.lost_allies(run.start, state),
            "screen": None, **(extra or {})}
