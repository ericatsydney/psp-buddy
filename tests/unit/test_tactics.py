"""Planner over live read dicts: fixtures use the retained 20-21 Oct Destiny / Mercurius values."""

import copy
import json
from dataclasses import replace
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


def test_strongest_boss_weapon_at_any_hp_when_the_threshold_is_zero() -> None:
    # User, 24 Oct: Mercurius, Vayeate and Wing Zero take no damage from weaker weapons, so the
    # turn policy uses "strongest boss weapons above 0%": a damaged boss still gets the strongest.
    from psp_buddy.policy import parse_policy
    policy = parse_policy("cheap weapons below 20%; strongest boss weapons above 0%")
    below = plan_attack(state(near_hp=10000, far_hp=24000), weapons(DESTINY_WEAPONS[1:4]), policy,
                        DESTINY, bosses=frozenset({NEAR_FOE}))
    assert attack(below)["attack"]["slot"] == 3 and below["expect"]["rule"] == "strongest"


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


TAURUS = 149301208       # (12,16) 2603/6600, far from Destiny
NEAR_TAURUS = 149301312


def test_bosses_by_name_or_by_twice_the_median_max_hp() -> None:
    from psp_buddy.tactics import boss_objects
    foes = state(extra=[unit(TAURUS, 12, 16, 12, 2603, 6600, ready=False)])["units"]
    names = {NEAR_FOE: "Mercurius", FAR_FOE: "Vayeate", TAURUS: "Taurus", THIRD: "WingGundamZero"}
    # by name only (HP factor off): spaces, "・" and case do not matter; allies and the third
    # force are never bosses
    assert boss_objects(foes, names, ["mercurius", "Wing Gundam Zero"], factor=0) == {NEAR_FOE}
    # by HP only: median of 6600, 24000, 26000 is 24000 -> nobody reaches 48000
    assert boss_objects(foes, {}, [], factor=2) == frozenset()
    two_taurus = foes + [unit(NEAR_TAURUS, 12, 15, 12, 4104, 6600, ready=False)]
    # median of 6600, 6600, 24000, 26000 is 15300 -> 26000 < 30600: still none; factor 1.5 -> both
    assert boss_objects(two_taurus, {}, [], factor=2) == frozenset()
    assert boss_objects(two_taurus, {}, [], factor=1.5) == {NEAR_FOE, FAR_FOE}
    assert boss_objects(two_taurus, names, ["Vayeate"], factor=1.5) == {NEAR_FOE, FAR_FOE}


def test_live_turn7_foes_make_mercurius_and_vayeate_bosses_by_hp() -> None:
    from psp_buddy.tactics import boss_objects
    foes = [unit(1, 12, 16, 12, 2603, 6600), unit(2, 12, 15, 12, 4104, 6600),
            unit(3, 12, 17, 12, 5211, 9600), unit(FAR_FOE, 16, 8, 12, 13393, 24000),
            unit(NEAR_FOE, 18, 8, 12, 10507, 26000)]
    assert boss_objects(foes, {}, []) == {FAR_FOE, NEAR_FOE}


def test_non_bosses_first_when_the_policy_says_so() -> None:
    near_grunt = unit(TAURUS, 17, 9, 12, 6600, 6600, ready=False)   # undamaged, in reach
    s = state(extra=[near_grunt])
    plain = attack(plan_attack(s, weapons(), POLICY, DESTINY, bosses={NEAR_FOE, FAR_FOE}))
    assert plain["attack"]["target_object"] == NEAR_FOE               # damaged boss first
    policy = parse_policy("target non-bosses before bosses")
    first = attack(plan_attack(s, weapons(), policy, DESTINY, bosses={NEAR_FOE, FAR_FOE}))
    assert first["attack"]["target_object"] == TAURUS
    # with no grunt in reach a boss is still attacked
    alone = attack(plan_attack(state(), weapons(), policy, DESTINY, bosses={NEAR_FOE, FAR_FOE}))
    assert alone["attack"]["target_object"] == NEAR_FOE


def test_a_group_13_pillar_fragment_is_attacked_and_third_force_group_5_is_not() -> None:
    # Stage 33 (26 Oct offline decode): fragments read group 13, the third force group 5.
    pillar = unit(7, 19, 7, 13, 6000, 6000, ready=False)
    beast = unit(8, 19, 6, 5, 2000, 29000, ready=False)            # damaged and nearer
    s = {"turn": {"turn": 5}, "units": [unit(DESTINY, 19, 5, 0, 5200, 5200, 230), pillar, beast],
         "reachable": [[19, 4, 1], [20, 5, 1]]}
    planned = attack(plan_attack(s, weapons(), POLICY, DESTINY))
    assert planned["attack"]["target_object"] == 7


def test_boss_objects_count_group_13_foes() -> None:
    from psp_buddy.tactics import boss_objects
    foes = [unit(1, 0, 0, 13, 6000, 6000), unit(2, 0, 1, 13, 7500, 7500),
            unit(3, 0, 2, 13, 30000, 30000), unit(4, 0, 3, 5, 90000, 90000)]
    assert boss_objects(foes, {}, []) == {3}


# M16 ally safety (3 Nov): turn-1 hold without Focus/Sense; advance when nothing is in reach.
SAFETY = parse_policy("hold units without focus or sense on turn 1; "
                      "advance toward foes when none is in reach")


def far_state(turn: int = 1, reachable: list[list[int]] | None = None) -> dict[str, Any]:
    """Foes far to the south (rows 20+), nothing in reach even after moving."""
    s = state(reachable=reachable)
    s["turn"] = {"turn": turn}
    for u in s["units"]:
        if u["object"] == FAR_FOE:
            u["tile_x"], u["tile_y"] = 16, 22
        elif u["object"] == NEAR_FOE:
            u["tile_x"], u["tile_y"] = 21, 20
    return s


# Stop-byte fallback (user, 10 Nov): cost byte 12 empty, byte 2 marks where the unit can stop.
def stop_marks(radius: int = 3) -> set[tuple[int, int]]:
    return {(19 + dx, 5 + dy) for dx in range(-radius, radius + 1)
            for dy in range(-radius, radius + 1) if 0 < abs(dx) + abs(dy) <= radius}


def with_stop_byte(s: dict[str, Any], marks: set[tuple[int, int]] | None = None) -> dict[str, Any]:
    marked = stop_marks() if marks is None else marks
    s["reachable"] = []
    s["screen"] = "move_range"
    s["map"] = {"cost_rows": ["." * 30] * 30,
                "stop_rows": ["".join("1" if (x, y) in marked else "." for x in range(30))
                              for y in range(30)]}
    return s


def moving(rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {**weapons(rows), "move": 3}


def test_stop_byte_unit_advances_and_says_where_the_range_came_from() -> None:
    result = plan_attack(with_stop_byte(far_state(turn=2)), moving(), SAFETY, DESTINY, turn=2)
    assert "attack" not in attack(result) and tuple(attack(result)["move_to"]) in stop_marks()
    assert result["expect"] == {"rule": "advance", "toward": NEAR_FOE, "distance": 14,
                                "range_source": "stop_byte"}


def test_stop_byte_unit_never_plans_an_attack_after_moving() -> None:
    short = [weapon(4, "ArondightSword", 4500, 1, 3, p=True, en_cost=35)]
    result = plan_attack(with_stop_byte(state()), moving(short), POLICY, DESTINY)
    assert result == {"handover": True, "reason": "no_target"}
    advance = plan_attack(with_stop_byte(state()), moving(short), SAFETY, DESTINY, turn=2)
    assert "attack" not in attack(advance) and advance["expect"]["rule"] == "advance"


def test_stop_byte_unit_still_attacks_from_its_own_tile() -> None:
    result = plan_attack(with_stop_byte(state()), moving(), POLICY, DESTINY)
    assert "move_to" not in attack(result) and "attack" in attack(result)
    assert "range_source" not in result["expect"]


def test_stop_byte_damaged_unit_retreats() -> None:
    policy = parse_policy("move damaged units away from foes")
    short = [weapon(0, "Saber", 2000, 1, 1, p=True)]
    result = plan_attack(with_stop_byte(state(hp=100)), moving(short), policy, DESTINY)
    assert result["expect"]["rule"] == "retreat" and result["expect"]["range_source"] == "stop_byte"
    assert tuple(attack(result)["move_to"]) in stop_marks() and "attack" not in attack(result)


def test_stop_byte_tiles_still_obey_the_foe_limit_and_the_turn_one_hold() -> None:
    limited = replace(SAFETY, max_foes_in_reach=1)
    every_tile = {FAR_FOE: 99, NEAR_FOE: 99}
    assert plan_attack(with_stop_byte(far_state(turn=2)), moving(), limited, DESTINY, turn=2,
                       foe_reach=every_tile) == {"handover": True, "reason": "no_target"}
    assert plan_attack(with_stop_byte(far_state(turn=1)), moving(), SAFETY, DESTINY, turn=1) == {
        "handover": True, "reason": "held_turn_one"}


def test_stop_byte_is_ignored_without_the_move_window_or_a_valid_range() -> None:
    closed = with_stop_byte(far_state(turn=2))
    closed["screen"] = "no_menu"
    too_far = with_stop_byte(far_state(turn=2), stop_marks() | {(19, 12)})
    for s in (closed, too_far):
        assert plan_attack(s, moving(), SAFETY, DESTINY, turn=2)["reason"] == "no_target"
    assert plan_attack(with_stop_byte(far_state(turn=2)), weapons(), SAFETY, DESTINY,
                       turn=2)["reason"] == "no_target"          # move stat unreadable


def test_spirited_needs_learned_focus_or_sense() -> None:
    from psp_buddy.tactics import spirited

    def pilot(*rows: tuple[str | None, bool]) -> dict[str, Any]:
        return {"spirits": [{"name": n, "learned": learned} for n, learned in rows]}

    assert spirited(pilot(("Focus", True)))
    assert spirited(pilot(("Alert", True), ("Sense", True)))
    assert not spirited(pilot(("Alert", True), ("Invincible", True)))
    assert not spirited(pilot(("Focus", False), ("Sense", False)))
    assert not spirited(pilot((None, True)))
    assert not spirited({})


def test_unspirited_unit_on_turn_one_is_held_when_nothing_is_in_reach_from_its_tile() -> None:
    s = far_state(turn=1)
    assert plan_attack(s, weapons(), SAFETY, DESTINY, turn=1) == {
        "handover": True, "reason": "held_turn_one"}


def test_unspirited_unit_on_turn_one_attacks_without_moving_only() -> None:
    # The near foe is in reach from (19,5) only after a move: a held unit does not take it.
    move_only = state(reachable=[[19, 6, 1], [19, 7, 2]])
    move_only["turn"] = {"turn": 1}
    for u in move_only["units"]:
        if u["object"] == NEAR_FOE:
            u["tile_x"], u["tile_y"] = 19, 9
        elif u["object"] == FAR_FOE:
            u["tile_x"], u["tile_y"] = 2, 30
    only_short = [weapon(0, "Saber", 2000, 1, 2, p=True)]
    held = plan_attack(move_only, weapons(only_short), SAFETY, DESTINY, turn=1)
    assert held == {"handover": True, "reason": "held_turn_one"}
    free = plan_attack(move_only, weapons(only_short), SAFETY, DESTINY, turn=1, spirited=True)
    assert attack(free)["move_to"] == [19, 7]
    in_place = plan_attack(state(), weapons(), SAFETY, DESTINY, turn=1)
    assert "move_to" not in attack(in_place)


def test_unreadable_turn_counts_as_turn_one() -> None:
    assert plan_attack(far_state(), weapons(), SAFETY, DESTINY, turn=None)["reason"] == (
        "held_turn_one")


def test_spirited_unit_advances_to_the_tile_closest_to_the_nearest_foe() -> None:
    reach = [[19, 4, 1], [19, 6, 1], [20, 5, 1], [19, 7, 2], [20, 6, 2], [20, 7, 3]]
    result = plan_attack(far_state(turn=1, reachable=reach), weapons(), SAFETY, DESTINY,
                         turn=1, spirited=True)
    assert result == {"act": {"unit_object": DESTINY, "move_to": [20, 7]},
                      "expect": {"rule": "advance", "toward": NEAR_FOE, "distance": 14}}


def test_any_unit_advances_from_turn_two() -> None:
    result = plan_attack(far_state(turn=2), weapons(), SAFETY, DESTINY, turn=2)
    assert attack(result)["move_to"] == [19, 7] and "attack" not in attack(result)


def test_advance_ties_go_to_the_cheaper_tile_then_the_lower_tile() -> None:
    s = far_state(turn=2, reachable=[[19, 6, 1], [18, 6, 2], [20, 6, 3]])
    for u in s["units"]:
        if u["object"] == NEAR_FOE:
            u["tile_x"], u["tile_y"] = 19, 20      # (19,6) 14, (18,6)/(20,6) 15
        elif u["object"] == FAR_FOE:
            u["tile_x"], u["tile_y"] = 30, 30
    assert attack(plan_attack(s, weapons(), SAFETY, DESTINY, turn=2))["move_to"] == [19, 6]
    s["reachable"] = [[19, 4, 1], [20, 7, 3], [18, 7, 4]]       # both 14 from (19,20)
    assert attack(plan_attack(s, weapons(), SAFETY, DESTINY, turn=2))["move_to"] == [20, 7]
    s["reachable"] = [[19, 4, 1], [20, 7, 3], [18, 7, 3]]
    assert attack(plan_attack(s, weapons(), SAFETY, DESTINY, turn=2))["move_to"] == [18, 7]


def test_advance_skips_occupied_tiles_and_third_force_units() -> None:
    s = far_state(turn=2, reachable=[[19, 6, 1], [19, 7, 2], [18, 4, 2]])
    s["units"].append(unit(5, 19, 7, 0, 1000, 1000))
    # The living third-force unit at (18,4) is nearer than any foe but is not advanced toward.
    assert attack(plan_attack(s, weapons(), SAFETY, DESTINY, turn=2))["move_to"] == [19, 6]


def test_no_advance_when_no_tile_is_closer_or_the_overlay_is_missing() -> None:
    behind = far_state(turn=2, reachable=[[19, 4, 1], [20, 4, 2]])
    assert plan_attack(behind, weapons(), SAFETY, DESTINY, turn=2)["reason"] == "no_target"
    none = far_state(turn=2, reachable=[])
    assert plan_attack(none, weapons(), SAFETY, DESTINY, turn=2)["reason"] == "no_target"


def test_without_the_clauses_nothing_changes() -> None:
    assert plan_attack(far_state(turn=1), weapons(), POLICY, DESTINY, turn=1)["reason"] == (
        "no_target")
    assert plan_attack(far_state(turn=2), weapons(), POLICY, DESTINY, turn=2)["reason"] == (
        "no_target")


# M16 (user, 3 Nov: "Limit foes in reach"): a move may not end where more than N foes can reach the
# unit next enemy phase (foe move + longest weapon range, Manhattan, terrain ignored).
LIMITED = parse_policy("end moves within reach of at most 1 foes")


def reach_state() -> dict[str, Any]:
    """Destiny at (10,10), move-range diamond of radius 4; foe A (10,14) damaged, B (12,12)."""
    units = [unit(DESTINY, 10, 10, 0, 5200, 5200, 230),
             unit(NEAR_FOE, 10, 14, 12, 5000, 26000, ready=False),
             unit(FAR_FOE, 12, 12, 12, 24000, 24000, ready=False)]
    reach = [[10 + dx, 10 + dy, abs(dx) + abs(dy)] for dx in range(-4, 5) for dy in range(-4, 5)
             if 0 < abs(dx) + abs(dy) <= 4]
    return {"turn": {"turn": 3}, "units": units, "reachable": reach}


SHORT = [weapon(0, "Saber", 2000, 1, 2, p=True)]


def test_a_move_skips_tiles_more_foes_can_reach_than_the_limit() -> None:
    reach = {NEAR_FOE: 2, FAR_FOE: 2}
    free = plan_attack(reach_state(), weapons(SHORT), POLICY, DESTINY, foe_reach=reach)
    assert attack(free)["move_to"] == [10, 12]           # nearest attack tile: A and B reach it
    safe = plan_attack(reach_state(), weapons(SHORT), LIMITED, DESTINY, foe_reach=reach)
    assert attack(safe)["move_to"] == [10, 13]           # only A reaches it


def test_an_unknown_foe_reach_counts_as_reaching_every_tile() -> None:
    none = parse_policy("end moves within reach of at most 0 foes")
    result = plan_attack(reach_state(), weapons(SHORT), none, DESTINY,
                         foe_reach={NEAR_FOE: 0})       # B unknown: it reaches every tile
    assert result == {"handover": True, "reason": "no_target"}


def test_attacking_from_the_own_tile_is_never_limited() -> None:
    s = reach_state()
    s["units"][1]["tile_y"] = 11                          # A next to Destiny
    result = plan_attack(s, weapons(SHORT), LIMITED, DESTINY, foe_reach={NEAR_FOE: 9, FAR_FOE: 9})
    assert "move_to" not in attack(result)


def test_an_advance_stops_where_the_limit_allows() -> None:
    s = far_state(turn=2, reachable=[[19, 6, 1], [19, 7, 2], [20, 7, 3]])
    policy = parse_policy("advance toward foes when none is in reach; "
                          "end moves within reach of at most 0 foes")
    # NEAR (21,20) reaches 13: (20,7) is 14 away, (19,7) 15: both out of reach; with 14 neither.
    assert attack(plan_attack(s, weapons(), policy, DESTINY, turn=2,
                              foe_reach={NEAR_FOE: 13, FAR_FOE: 1}))["move_to"] == [20, 7]
    assert attack(plan_attack(s, weapons(), policy, DESTINY, turn=2,
                              foe_reach={NEAR_FOE: 14, FAR_FOE: 1}))["move_to"] == [19, 7]
    assert plan_attack(s, weapons(), policy, DESTINY, turn=2,
                       foe_reach={NEAR_FOE: 16, FAR_FOE: 1})["reason"] == "no_target"


def test_foe_reach_is_move_plus_the_longest_weapon_a_moved_foe_can_use() -> None:
    from psp_buddy.tactics import foe_reach_of
    read = {"move": 5, "weapons": [weapon(0, "Gun", 1, 1, 3, p=True),
                                   weapon(1, "Cannon", 1, 2, 7, p=False),
                                   dict(weapon(2, "Map", 1, 1, 9, p=True), flags={"p": True,
                                                                               "map": True})]}
    assert foe_reach_of(read) == 8                       # max(5 + 3, 7); MAP weapons ignored
    assert foe_reach_of({"move": 4, "weapons": []}) == 4
    assert foe_reach_of({"weapons": []}) is None          # move unreadable: unknown
    # Effective move (11 Nov): a foe with Dash reaches by `move`, not the stored value.
    assert foe_reach_of({"move": 8, "stored_move": 7, "weapons": []}) == 8


# M16 (m16-i feedback, 3 Nov): strongest weapon above 10% foe HP; damaged units attack safely or
# move away from the foes.
STRONG = parse_policy("cheap weapons below 10%; strongest weapons above 10%")


def test_strongest_weapon_on_any_foe_above_the_threshold() -> None:
    result = plan_attack(state(), weapons(), STRONG, DESTINY)       # NEAR at 40%
    assert attack(result) == {"unit_object": DESTINY, "move_to": [19, 6], "attack": {
        "weapon": "ArondightSword", "slot": 4, "target_object": NEAR_FOE}}
    assert result["expect"]["rule"] == "strongest"
    low = plan_attack(state(near_hp=2000), weapons(), STRONG, DESTINY)   # 7.7%: cheap first
    assert attack(low)["attack"]["slot"] == 1 and low["expect"]["rule"] == "cheap"


def test_strongest_falls_back_to_the_strongest_weapon_that_reaches() -> None:
    no_move = state(reachable=[])                  # Arondight (range 3) needs a move
    assert attack(plan_attack(no_move, weapons(), STRONG, DESTINY))["attack"]["slot"] == 3


DAMAGED = parse_policy("move damaged units away from foes; "
                       "end moves within reach of at most 1 foes")


def hurt_reach_state(a_tile: tuple[int, int] = (10, 11)) -> dict[str, Any]:
    s = reach_state()
    s["units"][0]["hp"] = 3000                     # 57% < heal 70%
    s["units"][1]["tile_x"], s["units"][1]["tile_y"] = a_tile
    return s


def test_damaged_unit_attacks_from_the_tile_fewest_foes_reach() -> None:
    reach = {NEAR_FOE: 1, FAR_FOE: 2}
    healthy = hurt_reach_state()
    healthy["units"][0]["hp"] = 5200
    assert "move_to" not in attack(plan_attack(healthy, weapons(SHORT), LIMITED, DESTINY,
                                               foe_reach=reach))
    # (10,10) is reached by A; (9,10) is 2 from A and 5 from B: no foe reaches it.
    result = plan_attack(hurt_reach_state(), weapons(SHORT), DAMAGED, DESTINY, foe_reach=reach)
    assert attack(result)["move_to"] == [9, 10]


def test_damaged_unit_own_tile_is_limited_and_it_retreats_instead() -> None:
    result = plan_attack(hurt_reach_state(), weapons(SHORT), DAMAGED, DESTINY,
                         foe_reach={NEAR_FOE: 9, FAR_FOE: 9})
    # Every tile is reached by both foes: the farthest from the nearest foe (5), then lower tile.
    assert result == {"act": {"unit_object": DESTINY, "move_to": [6, 10]},
                      "expect": {"rule": "retreat", "threats": 2, "distance": 5}}


def test_damaged_unit_stays_when_no_tile_is_safer() -> None:
    s = hurt_reach_state(a_tile=(10, 14))
    s["reachable"] = [[10, 11, 1]]                  # only toward the foes
    assert plan_attack(s, weapons(SHORT), DAMAGED, DESTINY,
                       foe_reach={NEAR_FOE: 9, FAR_FOE: 9}) == {
        "handover": True, "reason": "retreat_stay"}


def test_damaged_unit_without_the_overlay_waits_for_it() -> None:
    s = hurt_reach_state(a_tile=(10, 14))
    s["reachable"] = []
    assert plan_attack(s, weapons(SHORT), DAMAGED, DESTINY,
                       foe_reach={NEAR_FOE: 9, FAR_FOE: 9})["reason"] == "no_target"


def test_damaged_unit_without_a_limit_attacks_like_a_healthy_one() -> None:
    policy = parse_policy("move damaged units away from foes")
    assert attack(plan_attack(state(hp=3000), weapons(), policy, DESTINY)) == attack(
        plan_attack(state(), weapons(), POLICY, DESTINY))


def test_damaged_unit_retreats_even_on_turn_one_when_held() -> None:
    policy = parse_policy("hold units without focus or sense on turn 1; "
                          "move damaged units away from foes")
    s = far_state(turn=1)
    s["units"][0]["hp"] = 3000
    result = plan_attack(s, weapons(), policy, DESTINY, turn=1)
    assert result["act"] == {"unit_object": DESTINY, "move_to": [19, 4]}
    assert result["expect"] == {"rule": "retreat", "threats": 2, "distance": 18}


def test_damaged_unit_prefers_a_safer_attack_on_a_lower_priority_foe() -> None:
    # Review 3 Nov: A (most damaged) is attackable only from tiles A reaches; B from a tile no
    # foe reaches, so the damaged unit attacks B.
    s = hurt_reach_state(a_tile=(10, 14))
    result = plan_attack(s, weapons(SHORT), DAMAGED, DESTINY,
                         foe_reach={NEAR_FOE: 2, FAR_FOE: 0})
    assert attack(result)["attack"]["target_object"] == FAR_FOE
    assert attack(result)["move_to"] == [11, 11]
