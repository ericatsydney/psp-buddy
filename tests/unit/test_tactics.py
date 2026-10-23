"""Planner over live read dicts: fixtures use the retained 20-21 Oct Destiny / Mercurius values."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from psp_buddy.models import Policy
from psp_buddy.policy import parse_policy
from psp_buddy.tactics import plan_attack

DESTINY = 149303288
NEAR_FOE = 149302976     # (18,8), 10507/26000
FAR_FOE = 149302872      # (16,8), 13393/24000
THIRD = 149299544        # group 4, (18,4)
POLICY = parse_policy("")


def unit(obj: int, x: int, y: int, group: int, hp: int, max_hp: int, en: int = 100,
         *, ready: bool = True) -> dict[str, Any]:
    return {"object": obj, "mech_id": 1, "pilot_id": 1, "hp": hp, "max_hp": max_hp, "en": en,
            "max_en": 230, "sp": 50, "tile_x": x, "tile_y": y, "raw_menu_group_byte": group,
            "counter_value": 1 if ready else 0, "counted_as_unmoved": ready}


def weapon(slot: int, name: str, power: int, lo: int, hi: int, *, p: bool, ammo: int | None = None,
           max_ammo: int = 0, en_cost: int = 0, will: int = 0) -> dict[str, Any]:
    return {"name": name, "slot": slot, "power": power, "min_range": lo, "max_range": hi,
            "max_ammo": max_ammo, "ammo": ammo, "en_cost": en_cost, "flags": {"p": p},
            "will": will}


# Destiny's list from act1-run-20261020T2204 (powers include upgrade and part bonus).
DESTINY_WEAPONS = [
    weapon(0, "17.5mmCIWS", 2200, 1, 3, p=True, ammo=10, max_ammo=10),
    weapon(1, "HiEnergyBeamGun", 3200, 2, 7, p=False, ammo=8, max_ammo=8),
    weapon(2, "RQM60FFlashEdge2", 3400, 1, 5, p=True, en_cost=5),
    weapon(3, "HiEnergyBeamGun", 4400, 3, 8, p=False, en_cost=35),
    weapon(4, "ArondightSword", 4500, 1, 3, p=True, en_cost=35),
]


def state(*, hp: int = 5200, reachable: list[list[int]] | None = None, ready: bool = True,
          near_hp: int = 10507, far_hp: int = 13393,
          extra: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    units = [
        unit(DESTINY, 19, 5, 0, hp, 5200, 230, ready=ready),
        unit(149303496, 18, 5, 0, 5300, 5300),
        unit(THIRD, 18, 4, 4, 1225, 16000, ready=False),
        unit(FAR_FOE, 16, 8, 12, far_hp, 24000, ready=False),
        unit(NEAR_FOE, 18, 8, 12, near_hp, 26000, ready=False),
        *(extra or []),
    ]
    if reachable is None:       # ring of cost-1/2 tiles around (19,5), like a real overlay
        reachable = [[19, 4, 1], [19, 6, 1], [20, 5, 1], [18, 5, 1], [19, 7, 2], [20, 6, 2]]
    return {"turn": {"turn": 7}, "units": units, "reachable": reachable}


def weapons(rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"object": DESTINY, "weapons": copy.deepcopy(DESTINY_WEAPONS if rows is None else rows)}


def attack(result: dict[str, Any]) -> dict[str, Any]:
    assert "handover" not in result, result
    act: dict[str, Any] = result["act"]
    return act


def test_attack_from_current_tile_uses_median_weapon_on_most_damaged_foe() -> None:
    act = attack(plan_attack(state(), weapons(), POLICY, DESTINY))
    assert act == {"unit_object": DESTINY,
                   "attack": {"weapon": "RQM60FFlashEdge2", "slot": 2, "target_object": NEAR_FOE}}


def test_move_then_attack_when_only_short_weapons_exist() -> None:
    short = [weapon(4, "ArondightSword", 4500, 1, 3, p=True, en_cost=35)]
    act = attack(plan_attack(state(), weapons(short), POLICY, DESTINY))
    assert act["move_to"] == [19, 6]          # nearest reachable tile within 3 of (18,8)
    assert act["attack"] == {"weapon": "ArondightSword", "slot": 4, "target_object": NEAR_FOE}


def test_boss_above_threshold_gets_strongest_weapon() -> None:
    result = plan_attack(state(near_hp=25000, far_hp=24000), weapons(DESTINY_WEAPONS[1:4]), POLICY,
                         DESTINY, bosses=frozenset({NEAR_FOE}))
    assert attack(result)["attack"]["slot"] == 3
    below = plan_attack(state(near_hp=10000, far_hp=24000), weapons(DESTINY_WEAPONS[1:4]), POLICY,
                        DESTINY,
                        bosses=frozenset({NEAR_FOE}))
    assert attack(below)["attack"]["slot"] == 2


def test_cheap_weapon_on_nearly_dead_foe() -> None:
    result = plan_attack(state(near_hp=3000), weapons(), POLICY, DESTINY)
    assert attack(result)["attack"]["slot"] == 1         # en_cost 0 beats 5 and 35
    assert result["expect"]["rule"] == "cheap"


def test_cheap_threshold_comes_from_policy() -> None:
    policy = parse_policy("cheap weapons below 50%")
    assert attack(plan_attack(state(), weapons(), policy, DESTINY))["attack"]["slot"] == 1


def test_injured_unit_hands_over_instead_of_attacking() -> None:
    result = plan_attack(state(hp=3000), weapons(), POLICY, DESTINY)    # 57% < heal 70%
    assert result == {"handover": True, "reason": "retreat_needed"}
    ok = plan_attack(state(hp=3700), weapons(), Policy(heal_below_percent=70), DESTINY)
    assert "act" in ok                                   # 71%


def test_no_target_in_reach_hands_over() -> None:
    far = state(reachable=[[19, 4, 1]])
    for u in far["units"]:
        if u["raw_menu_group_byte"] == 12:
            u["tile_x"], u["tile_y"] = 2, 2
    assert plan_attack(far, weapons(), POLICY, DESTINY) == {"handover": True,
                                                            "reason": "no_target"}


@pytest.mark.parametrize("breakage", ["no_unit", "no_weapons", "hp_unknown", "wrong_weapon_owner",
                                      "no_units"])
def test_unknown_data_hands_over(breakage: str) -> None:
    st, wp = state(), weapons()
    if breakage == "no_unit":
        st["units"] = [u for u in st["units"] if u["object"] != DESTINY]
    elif breakage == "no_weapons":
        del wp["weapons"]
    elif breakage == "hp_unknown":
        st["units"][0]["hp"] = None
    elif breakage == "wrong_weapon_owner":
        wp["object"] = 1
    else:
        del st["units"]
    result = plan_attack(st, wp, POLICY, DESTINY)
    assert result["handover"] is True
    assert str(result["reason"]).startswith("unknown_")


def test_duplicate_weapon_names_are_told_apart_by_slot() -> None:
    result = plan_attack(state(near_hp=25000, far_hp=24000), weapons(DESTINY_WEAPONS[1:4]), POLICY,
                         DESTINY, bosses=frozenset({NEAR_FOE}))
    chosen = attack(result)["attack"]
    assert chosen["weapon"] == "HiEnergyBeamGun" and chosen["slot"] == 3


def test_moving_drops_weapons_without_the_p_flag() -> None:
    # The target is 5 tiles away: the strong non-P rifle cannot be used after the move that is
    # needed to reach it, so only the weaker P saber qualifies.
    rows = [weapon(0, "BeamRifle", 4000, 1, 3, p=False), weapon(1, "Saber", 1000, 1, 3, p=True)]
    st = state()
    for u in st["units"]:
        if u["object"] == NEAR_FOE:
            u["tile_x"], u["tile_y"] = 19, 10
    act = attack(plan_attack(st, weapons(rows), POLICY, DESTINY))
    assert act["attack"]["slot"] == 1
    assert act["move_to"] == [19, 7]


def test_third_force_unit_is_never_a_target() -> None:
    only_third = state()
    only_third["units"] = [u for u in only_third["units"] if u["raw_menu_group_byte"] != 12]
    assert plan_attack(only_third, weapons(), POLICY, DESTINY)["reason"] == "no_target"
    assert attack(plan_attack(state(), weapons(), POLICY, DESTINY))["attack"][
        "target_object"] != THIRD


def test_move_never_ends_on_an_occupied_tile() -> None:
    short = [weapon(4, "ArondightSword", 4500, 1, 3, p=True, en_cost=35)]
    st = state(extra=[unit(149303999, 19, 6, 0, 5000, 5000)])
    assert attack(plan_attack(st, weapons(short), POLICY, DESTINY))["move_to"] != [19, 6]


def test_unusable_weapons_and_acted_unit() -> None:
    dry = [weapon(0, "Gun", 3000, 1, 9, p=True, ammo=0, max_ammo=5)]
    assert plan_attack(state(), weapons(dry), POLICY, DESTINY)["reason"] == "no_target"
    assert plan_attack(state(ready=False), weapons(), POLICY, DESTINY)["reason"] == "unit_not_ready"


def test_known_hit_chance_is_reported_and_zero_skips_target() -> None:
    result = plan_attack(state(), weapons(), POLICY, DESTINY, hits={NEAR_FOE: 60})
    assert result["expect"]["hit"] == 60
    assert result["expect"]["damage_model"] == "power"
    assert result["expect"]["expected_damage"] == 0.6 * 3400
    skipped = plan_attack(state(), weapons(), POLICY, DESTINY, hits={NEAR_FOE: 0})
    assert attack(skipped)["attack"]["target_object"] == FAR_FOE


def test_stale_reach_overlay_disables_moves() -> None:
    short = [weapon(4, "ArondightSword", 4500, 1, 3, p=True, en_cost=35)]
    stale = state(reachable=[[5, 5, 1], [6, 5, 1]])      # not centred on the unit
    assert plan_attack(stale, weapons(short), POLICY, DESTINY)["reason"] == "no_target"


def test_move_energy_is_reserved_before_choosing_a_move_weapon() -> None:
    short = [weapon(4, "ArondightSword", 4500, 1, 3, p=True, en_cost=35)]
    low = state()
    low["units"][0]["en"] = 35          # the 1-cost move leaves 34 < 35
    assert plan_attack(low, weapons(short), POLICY, DESTINY)["reason"] == "no_target"
    enough = state()
    enough["units"][0]["en"] = 36
    assert attack(plan_attack(enough, weapons(short), POLICY, DESTINY))["move_to"] == [19, 6]


def test_weapons_needing_more_will_than_assumed_are_never_chosen() -> None:
    rows = [weapon(0, "Gun", 1000, 1, 9, p=True),
            weapon(1, "Big", 9000, 1, 9, p=True, will=110)]
    chosen = attack(plan_attack(state(), weapons(rows), POLICY, DESTINY,
                                bosses=frozenset({NEAR_FOE})))
    assert chosen["attack"]["slot"] == 0          # will is not decoded: 100 is assumed
    ok = plan_attack(state(), weapons(rows), POLICY, DESTINY, bosses=frozenset({NEAR_FOE}),
                     will=130)
    assert attack(ok)["attack"]["slot"] in (0, 1)
    only_big = plan_attack(state(), weapons(rows[1:]), POLICY, DESTINY)
    assert only_big["reason"] == "no_target"


def test_only_weapons_with_a_certain_menu_row_are_chosen() -> None:
    # Strike Freedom (22 Oct live): SuperDragoon is a MAP weapon whose shown power (3600) differs
    # from memory (3700), so HiEnergy's row is unknown; MAP weapons are never chosen. Will does not
    # hide weapons (shown greyed); EN below a cost may, which makes every stronger row unknown.
    rows = [weapon(0, "CIWS", 2000, 1, 9, p=True),
            weapon(1, "Saber", 3200, 1, 9, p=True, en_cost=5),
            weapon(2, "Dragoon", 3700, 1, 9, p=True, will=0),
            weapon(3, "HiEnergy", 3600, 1, 9, p=True),
            weapon(4, "Calidus", 4100, 1, 9, p=True, en_cost=35)]
    rows[2]["flags"]["map"] = True
    rows[2]["base_power"] = 3500                         # shown 3500..3700 (live: 3600)
    for en, expected in ((230, 4), (40, 4), (4, 0)):
        st = state(near_hp=25000, far_hp=24000)          # a healthy boss: strongest usable weapon
        st["units"][0]["en"] = en
        result = plan_attack(st, weapons(rows), POLICY, DESTINY, bosses=frozenset({NEAR_FOE}))
        assert attack(result)["attack"]["slot"] == expected, en
    rows[4]["en_cost"] = 0
    rows[4]["flags"]["condition"] = True                 # hidden by the menu (record byte 26)
    st = state(near_hp=25000, far_hp=24000)
    result = plan_attack(st, weapons(rows), POLICY, DESTINY, bosses=frozenset({NEAR_FOE}))
    assert attack(result)["attack"]["slot"] == 1


def test_menu_rows_are_counted_in_power_order() -> None:
    # The menu lists weapons by power, lowest first (22 Oct live: Force Impulse). A possibly
    # hidden weapon only shifts the rows of stronger weapons; equal powers have no known order.
    boss = {"bosses": frozenset({NEAR_FOE})}
    rows = [weapon(0, "CIWS", 2000, 1, 9, p=True),
            weapon(1, "Super", 5000, 1, 9, p=True, en_cost=250),
            weapon(2, "Rifle", 3000, 1, 9, p=True)]
    st = state(near_hp=25000, far_hp=24000)
    assert attack(plan_attack(st, weapons(rows), POLICY, DESTINY, **boss))["attack"]["slot"] == 2
    tied = [weapon(0, "Bunker", 3100, 1, 9, p=True),
            weapon(1, "Eagle", 3100, 1, 9, p=True),
            weapon(2, "Vulcan", 2000, 1, 9, p=True)]
    assert attack(plan_attack(st, weapons(tied), POLICY, DESTINY, **boss))["attack"]["slot"] == 2


def test_excluded_slots_are_never_chosen() -> None:
    first = attack(plan_attack(state(), weapons(), POLICY, DESTINY))["attack"]["slot"]
    again = attack(plan_attack(state(), weapons(), POLICY, DESTINY, exclude={first}))
    assert again["attack"]["slot"] != first
    every = {w["slot"] for w in DESTINY_WEAPONS}
    assert plan_attack(state(), weapons(), POLICY, DESTINY, exclude=every)["reason"] == "no_target"


RETAINED = (Path(__file__).parents[2] / "local/move-attack-trial-20261017/spd4-run-20261021T2046"
            / "navigation-mailbox/nav-response-45abc2d4cbd8477e98354fd20c415286.json")


@pytest.mark.skipif(not RETAINED.exists(), reason="retained local run not present")
def test_retained_live_state_picks_flashedge_on_mercurius() -> None:
    live = json.loads(RETAINED.read_text(encoding="utf-8"))["result"]
    live["reachable"] = []               # nothing selected in that capture: current tile only
    result = plan_attack(live, weapons(), POLICY, DESTINY)
    assert attack(result)["attack"]["slot"] == 2
