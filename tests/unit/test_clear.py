import pytest

from psp_buddy import clear

ALLY, THIRD, FOE = 0, 4, 12
NAMES = {11: 'Mercurius', 12: 'Vayeate', 13: 'Euclid', 14: 'Taurus', 15: 'Taurus',
         20: 'Wing Gundam Zero'}


def unit(obj, group=FOE, hp=3000, max_hp=None, x=1, y=1, en=100, ready=False):
    return {'object': obj, 'raw_menu_group_byte': group, 'hp': hp,
            'max_hp': hp if max_hp is None else max_hp, 'tile_x': x, 'tile_y': y, 'en': en,
            'counted_as_unmoved': ready}


def allies():
    return [unit(1, ALLY, 5000, ready=True), unit(2, ALLY, 4700, ready=True)]


def start_units():
    return allies() + [unit(11, hp=10507), unit(12, hp=10500), unit(13, hp=5211),
                       unit(14, hp=2603), unit(15, hp=2843), unit(20, THIRD, hp=1225)]


def state(units, turn=7):
    return {'turn': {'turn': turn}, 'units': units}


def begun():
    return clear.begin(state(start_units()), NAMES)


def test_begin_freezes_the_named_bosses():
    run = begun()
    assert run.start_turn == 7
    assert run.bosses == frozenset({11, 12})


def test_two_bosses_left_is_cleared_although_the_median_now_equals_their_hp():
    run = clear.begin(state(start_units()), {})        # no names: bosses by max HP only
    assert run.bosses == frozenset({11, 12})
    later = state(allies() + [unit(11, hp=9000, max_hp=10507), unit(12, hp=10500)])
    assert clear.nonboss_left(run, later) == []
    assert clear.decide(run, later) == 'cleared'


def test_third_force_units_are_neither_bosses_nor_non_bosses():
    run = begun()
    assert 20 not in run.bosses
    only_third = state(allies() + [unit(11, hp=10507), unit(20, THIRD, hp=1225)])
    assert clear.nonboss_left(run, only_third) == []


def test_foes_at_zero_hp_or_gone_from_the_list_count_as_destroyed():
    run = begun()
    later = state(allies() + [unit(11, hp=10507), unit(13, hp=0, max_hp=5211),
                              unit(14, hp=50, max_hp=2603)])
    assert clear.nonboss_left(run, later) == [14]
    assert clear.decide(run, later) is None


def test_a_late_foe_is_a_boss_only_by_name():
    run = begun()
    big = state(allies() + [unit(11, hp=10507), unit(30, hp=50000)])
    assert clear.nonboss_left(run, big) == [30]
    late = state(allies() + [unit(31, hp=10507)])
    assert clear.nonboss_left(run, late) == [31]                       # name not read yet
    assert clear.nonboss_left(run, late, {**NAMES, 31: 'Mercurius'}) == []
    assert clear.decide(run, late, mech_names={**NAMES, 31: 'Mercurius'}) == 'cleared'


def test_an_ally_loss_comes_before_cleared():
    run = begun()
    later = state([unit(1, ALLY, 5000)] + [unit(11, hp=10507)])      # ally 2 vanished
    assert clear.decide(run, later) == 'ally_lost'
    zero = state([unit(1, ALLY, 5000), unit(2, ALLY, 0, max_hp=4700), unit(13, hp=10)])
    assert clear.decide(run, zero) == 'ally_lost'


def test_turn_budget_counts_player_turns_from_the_start():
    run = begun()
    units = allies() + [unit(13, hp=10, max_hp=5211)]
    assert clear.decide(run, state(units, turn=11)) is None
    assert clear.decide(run, state(units, turn=12)) == 'turn_budget'
    assert clear.decide(run, state(units, turn=9), budget=2) == 'turn_budget'


@pytest.mark.parametrize('bad', [{}, {'units': []}, {'units': start_units()},
                                 {'turn': {'turn': 7}, 'units': [{'object': 1}]}])
def test_an_unreadable_state_raises(bad):
    with pytest.raises(ValueError):
        clear.begin(bad, NAMES)
    with pytest.raises(ValueError):
        clear.decide(begun(), bad)


def test_status_is_the_turn_next_clear_field():
    run = begun()
    later = state(allies() + [unit(11, hp=10507), unit(14, hp=50, max_hp=2603)], turn=8)
    assert clear.status(run, later) == {'nonboss_left': [14], 'bosses': [11, 12], 'turn': 8}


def test_handover_report_lists_bosses_allies_and_destroyed_foes():
    run = begun()
    later = state([unit(1, ALLY, 4000, max_hp=5000, x=3, y=4, en=90, ready=True),
                   unit(11, hp=9000, max_hp=10507, x=16, y=8),
                   unit(20, THIRD, hp=669, max_hp=1225)], turn=8)
    rep = clear.handover_report(run, later, 'ally_lost', mech_names=NAMES,
                                extra={'turn_reports': ['turn-report-7.json']})
    assert rep['reason'] == 'ally_lost'
    assert rep['turns'] == [7, 8] and rep['turns_played'] == 2
    assert rep['bosses'] == [
        {'object': 11, 'name': 'Mercurius', 'hp': 9000, 'max_hp': 10507, 'tile': [16, 8]},
        {'object': 12, 'name': 'Vayeate', 'hp': 0, 'max_hp': 10500, 'tile': None}]
    assert rep['nonboss_destroyed'] == [13, 14, 15] and rep['nonboss_left'] == []
    assert rep['allies'] == [{'object': 1, 'hp': 4000, 'max_hp': 5000, 'en': 90, 'unmoved': True,
                              'tile': [3, 4]}]
    assert rep['lost'] == [2]
    assert rep['turn_reports'] == ['turn-report-7.json'] and rep['screen'] is None


def test_handover_report_lists_a_late_boss_known_by_name():
    run = begun()
    later = state(allies() + [unit(31, hp=8000, max_hp=10507, x=2, y=3)], turn=8)
    rep = clear.handover_report(run, later, 'cleared', mech_names={**NAMES, 31: 'Mercurius'})
    assert {'object': 31, 'name': 'Mercurius', 'hp': 8000, 'max_hp': 10507,
            'tile': [2, 3]} in rep['bosses']
    assert rep['nonboss_left'] == []


def test_the_name_key_is_shared_with_tactics():
    from psp_buddy import tactics
    assert tactics.name_key('Wing Gundam-Zero') == 'winggundamzero'
