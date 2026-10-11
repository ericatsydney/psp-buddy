import pytest

from psp_buddy.models import Policy
from psp_buddy.policy import parse_policy


def test_empty_uses_explicit_defaults():
    assert parse_policy('') == Policy()


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
