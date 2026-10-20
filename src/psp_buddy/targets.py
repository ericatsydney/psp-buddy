"""Which enemy units each weapon of one unit can hit from its current tile (memory data only).

Distance is Manhattan: on 18 Oct the 1~3 CIWS had no target for Destiny at (19,5) although foes
stood at Chebyshev distance 3, while the 3~8 gun reached the foes at (16,8) and (18,8).
Availability follows the 18 Oct rule: ammo/EN available and (not moved or the weapon has the
P flag).
Will requirements are not checked (the pilot's will is not decoded yet).
"""

import struct
from collections.abc import Mapping, Sequence

HOVER_HIT_ADDRESS = 0x08ED055C   # two s32; 18 Oct runs matched the on-screen HIT%
NO_TARGET = -10000
ENEMY_GROUP = 12          # raw_menu_group_byte: 0 = ally, 4 = third force (HIT 0%), 12 = foe


def _unit_tile(unit: Mapping[str, object]) -> tuple[int, int]:
    x, y = unit["tile_x"], unit["tile_y"]
    if not isinstance(x, int) or not isinstance(y, int):
        raise ValueError("unit has no tile")
    return x, y


def _unusable_reason(weapon: Mapping[str, object], en: int, moved: bool) -> str | None:
    flags = weapon.get("flags")
    if moved and not (isinstance(flags, Mapping) and flags.get("p")):
        return "moved"
    max_ammo, ammo, cost = weapon.get("max_ammo"), weapon.get("ammo"), weapon.get("en_cost")
    if isinstance(max_ammo, int) and max_ammo and not (isinstance(ammo, int) and ammo > 0):
        return "no_ammo"
    if isinstance(cost, int) and cost > en:
        return "no_en"
    return None


def targets_in_range(unit: Mapping[str, object], units: Sequence[Mapping[str, object]],
                     weapons: Mapping[str, object], *, moved: bool = False,
                     enemy_groups: Sequence[int] = (ENEMY_GROUP,)) -> dict[str, object]:
    """Per weapon: usable flag, reason if not, and the living enemies within min..max range.

    `unit` is a read_state unit (the acting one); `weapons` is the ppsspp_read_weapons answer.
    `moved` must be given by the caller: memory cannot tell a moved-but-unfinished unit.
    """
    found = [u for u in units if u.get("object") == unit.get("object")]
    if len(found) != 1:
        raise ValueError("acting unit must appear exactly once in the unit list")
    x, y = _unit_tile(found[0])
    en = unit.get("en")
    if not isinstance(en, int):
        raise ValueError("unit has no EN")
    foes = [(u, abs(_unit_tile(u)[0] - x) + abs(_unit_tile(u)[1] - y)) for u in units
            if u.get("raw_menu_group_byte") in enemy_groups
            and isinstance(u.get("hp"), int) and u["hp"] > 0]       # type: ignore[operator]
    rows = weapons.get("weapons")
    if not isinstance(rows, list):
        raise ValueError("weapons answer has no weapon list")
    result: list[dict[str, object]] = []
    for weapon in rows:
        reason = _unusable_reason(weapon, en, moved)
        low, high = weapon["min_range"], weapon["max_range"]
        targets = [] if reason else [
            {"object": u["object"], "tile": [u["tile_x"], u["tile_y"]], "distance": d,
             "hp": u["hp"]}
            for u, d in foes if low <= d <= high]
        result.append({"slot": weapon["slot"], "name": weapon.get("name"),
                       "min_range": low, "max_range": high, "usable": reason is None,
                       "unusable_reason": reason, "targets": targets})
    return {"object": unit["object"], "tile": [x, y], "moved": moved, "weapons": result}


def decode_hover_hit(blob: bytes) -> dict[str, object]:
    """Hit chance under the cursor in target select, from the two s32 at HOVER_HIT_ADDRESS.

    The fields read -10000 when the cursor is on a non-target and 24 while idle in menus, so
    the value is only a forecast while a weapon's target select is open (the caller knows).
    """
    if len(blob) != 8:
        raise ValueError("hover hit needs 8 bytes")
    first, second = struct.unpack("<ii", blob)
    if first != second:
        return {"state": "unknown", "hit": None}
    if first == NO_TARGET:
        return {"state": "no_target", "hit": None}
    if 0 <= first <= 100:
        return {"state": "hit", "hit": first}
    return {"state": "unknown", "hit": None}
