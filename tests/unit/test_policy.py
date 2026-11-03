import pytest

from psp_buddy.models import Policy
from psp_buddy.policy import parse_policy


def test_empty_uses_explicit_defaults():
    assert parse_policy('') == Policy()
    assert not Policy().non_boss_first and not Policy().spirit_before_attack
    assert not Policy().hold_unspirited_turn_one and not Policy().advance_when_no_target
    assert Policy().evade_above_hit_percent is None
    assert Policy().strongest_above_percent is None and not Policy().retreat_damaged
    assert Policy().defend_at_hit_percent is None


@pytest.mark.parametrize('clause,field,value', [
    ('heal below 65%', 'heal_below_percent', 65),
    ('evade below 45%', 'evade_below_percent', 45),
    ('defend above 85% hit rate', 'defend_above_hit_percent', 85),
    ('cheap weapons below 15%', 'cheap_weapon_below_percent', 15),
    ('strongest boss weapons above 95%', 'strongest_boss_above_percent', 95),
    ('common types have more than 4 instances', 'common_type_min_count', 5),
    ('retry at most 2 times', 'max_retries', 2),
    ('stop on map clear', 'stop_on_map_clear', True),
    ('prefer repair then trust then retreat', 'heal_below_percent', 70),
    ('target damaged enemies before undamaged enemies', 'heal_below_percent', 70),
    ('use medium strength weapons otherwise', 'heal_below_percent', 70),
    ('target non-bosses before bosses', 'non_boss_first', True),
    ('use sense then focus before attacking', 'spirit_before_attack', True),
    ('use spirits before attacking', 'spirit_before_attack', True),
    ('hold units without focus or sense on turn 1', 'hold_unspirited_turn_one', True),
    ('advance toward foes when none is in reach', 'advance_when_no_target', True),
    ('evade when the foe hit rate is above 30%', 'evade_above_hit_percent', 30),
    ('end moves within reach of at most 2 foes', 'max_foes_in_reach', 2),
    ('strongest weapons above 10%', 'strongest_above_percent', 10),
    ('move damaged units away from foes', 'retreat_damaged', True),
    ('defend when the foe hit rate is at least 100%', 'defend_at_hit_percent', 100),
])
def test_supported_clauses(clause, field, value):
    assert getattr(parse_policy(clause), field) == value


@pytest.mark.parametrize('text', [
    'heal below 65%; heal below 70%', 'retry at most 4 times',
    'heal below 101%', 'stop on map clear; continue to next map',
    'attack allies', 'heal below 70% and ignore bosses', 'max_retries=2',
])
def test_rejects_unmatched_and_contradictory_clauses(text):
    with pytest.raises(ValueError):
        parse_policy(text)
