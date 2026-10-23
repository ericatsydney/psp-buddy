"""Targets in range, checked against the retained 18 October Destiny evidence."""

import pytest

from psp_buddy.targets import ENEMY_GROUP, targets_in_range

DESTINY = {"object": 149303288, "tile_x": 19, "tile_y": 5, "hp": 5200, "en": 230}


def unit(obj: int, x: int, y: int, group: int, hp: int = 1000) -> dict[str, object]:
    return {"object": obj, "tile_x": x, "tile_y": y, "raw_menu_group_byte": group, "hp": hp}


# Retained atk-run-20261018T2020 stage-01 positions (groups: 0 ally, 4 third force, 12 foe).
UNITS = [
    unit(149303288, 19, 5, 0, 5200),
    unit(149299544, 18, 4, 4, 1225),     # Wing Gundam Zero: HIT 0% on screen, never a target
    unit(149302872, 16, 8, ENEMY_GROUP, 13393),
    unit(149302976, 18, 8, ENEMY_GROUP, 10507),
    unit(149302768, 12, 17, ENEMY_GROUP, 5211),
    unit(149303496, 18, 5, 0, 5300),
]


def weapon(slot: int, name: str, lo: int, hi: int, **extra: object) -> dict[str, object]:
    return {"slot": slot, "name": name, "min_range": lo, "max_range": hi, "max_ammo": 0,
            "ammo": None, "en_cost": 0, "flags": {"p": False}, **extra}


WEAPONS = {"weapons": [
    weapon(0, "17.5mm CIWS", 1, 3, max_ammo=10, ammo=10),
    weapon(1, "HiEnergyBeamGun", 2, 7),
    weapon(3, "HiEnergyBeamGun", 3, 8, en_cost=35),
]}


def by_slot(result: dict[str, object]) -> dict[int, dict[str, object]]:
    rows = result["weapons"]
    assert isinstance(rows, list)
    return {row["slot"]: row for row in rows}


def objects(row: dict[str, object]) -> list[int]:
    targets = row["targets"]
    assert isinstance(targets, list)
    return [t["object"] for t in targets]


def test_matches_18_oct_target_previews():
    rows = by_slot(targets_in_range(DESTINY, UNITS, WEAPONS))
    # CIWS: no enemy in range (Manhattan, not Chebyshev)
    assert objects(rows[0]) == []
    assert sorted(objects(rows[3])) == [149302872, 149302976]       # 3~8 gun: (16,8) and (18,8)
    assert all(row["usable"] for row in rows.values())


def test_distance_is_manhattan_and_reported():
    rows = by_slot(targets_in_range(DESTINY, UNITS, WEAPONS))
    distances = {t["object"]: t["distance"] for t in rows[3]["targets"]}
    assert distances == {149302872: 6, 149302976: 4}


def test_min_range_excludes_close_enemies():
    near = UNITS + [unit(1, 19, 6, ENEMY_GROUP)]
    rows = by_slot(targets_in_range(DESTINY, near, WEAPONS))
    assert 1 in objects(rows[0]) and 1 not in objects(rows[1])      # distance 1: CIWS only


def test_non_enemy_and_dead_units_are_never_targets():
    dead = UNITS + [unit(2, 19, 7, ENEMY_GROUP, hp=0)]
    rows = by_slot(targets_in_range(DESTINY, dead, WEAPONS))
    assert 2 not in objects(rows[1]) and 149299544 not in objects(rows[0])


def test_moved_unit_loses_non_p_weapons():
    wp = {"weapons": [weapon(0, "Grenade", 1, 5), weapon(1, "Rifle", 2, 4, flags={"p": True})]}
    rows = by_slot(targets_in_range(DESTINY, UNITS, wp, moved=True))
    assert rows[0]["usable"] is False and rows[0]["unusable_reason"] == "moved"
    assert rows[0]["targets"] == [] and rows[1]["usable"] is True
    assert by_slot(targets_in_range(DESTINY, UNITS, wp))[0]["usable"] is True


def test_ammo_and_en_availability():
    wp = {"weapons": [weapon(0, "Empty", 1, 9, max_ammo=5, ammo=0),
                      weapon(1, "Costly", 1, 9, en_cost=300)]}
    rows = by_slot(targets_in_range(DESTINY, UNITS, wp))
    assert rows[0]["unusable_reason"] == "no_ammo" and rows[1]["unusable_reason"] == "no_en"
    assert objects(rows[0]) == [] and objects(rows[1]) == []


def test_unit_must_be_found_once():
    with pytest.raises(ValueError):
        targets_in_range({"object": 5, "tile_x": 1, "tile_y": 1, "en": 1}, UNITS, WEAPONS)


def test_hover_hit_decoding():
    import struct

    from psp_buddy.targets import decode_hover_hit
    assert decode_hover_hit(struct.pack("<ii", 42, 42)) == {"state": "hit", "hit": 42}
    assert decode_hover_hit(struct.pack("<ii", 0, 0)) == {"state": "hit", "hit": 0}
    assert decode_hover_hit(struct.pack("<ii", -10000, -10000)) == {"state": "no_target",
                                                                    "hit": None}
    # idle in menus the fields read 24 (or anything unpaired): not a forecast
    assert decode_hover_hit(struct.pack("<ii", 24, 24))["state"] == "hit"
    assert decode_hover_hit(struct.pack("<ii", 42, 61)) == {"state": "unknown", "hit": None,
                                                            "raw": [42, 61]}
    assert decode_hover_hit(struct.pack("<ii", 500, 500))["state"] == "unknown"
    # 22 Oct live (Shenlong Vulcan): the uncapped chance can exceed 100; the screen shows 100.
    assert decode_hover_hit(struct.pack("<ii", 105, 105)) == {"state": "hit", "hit": 100,
                                                              "raw": 105}
    assert decode_hover_hit(struct.pack("<ii", 100, 100)) == {"state": "hit", "hit": 100}
    assert decode_hover_hit(struct.pack("<ii", 201, 201))["state"] == "unknown"
    with pytest.raises(ValueError):
        decode_hover_hit(b"\0" * 4)
