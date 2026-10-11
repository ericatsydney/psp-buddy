from dataclasses import replace

from psp_buddy.models import (
    Action,
    ActionKind,
    Affiliation,
    Phase,
    Policy,
    Prediction,
    Screen,
    Snapshot,
    Unit,
    ValidationStatus,
    Weapon,
)
from psp_buddy.planner import choose_action


def unit(id, affiliation=Affiliation.ALLY, hp=100, **kwargs):
    values = dict(position=(0, 0), hp=hp, max_hp=100, en=100, max_en=100,
                  action_available=True, defeated=False, scripted_departure=False,
                  repair_capable=False, trust_capable=False, weapons=(), legal_moves=())
    values.update(kwargs)
    return Unit(id, id, affiliation, **values)


def battle(units, actions, predictions=()):
    return Snapshot(1, 'map', 'game', 'patch', 'capture', 'profile',
                    ValidationStatus.VALIDATED, phase=Phase.PLAYER, screen=Screen.MAP,
                    units=tuple(units), legal_actions=tuple(actions), predictions=predictions,
                    map_complete=False)


def attack(target, weapon='w', actor='ally'):
    return Action(ActionKind.ATTACK, 1, actor, target, weapon)


def weapon(id='w', power=100, en_cost=0, ammo_cost=0, ammo=0):
    return Weapon(id, power, en_cost, ammo_cost, ammo, 1, 5, True, False, False,
                  ('damaged', 'full', 'enemy'))


def test_damaged_enemy_precedes_nearer_full_health():
    ally = unit('ally', weapons=(weapon(),))
    damaged = unit('damaged', Affiliation.ENEMY, 90, position=(5, 0))
    full = unit('full', Affiliation.ENEMY, position=(1, 0))
    actions = [attack('full'), attack('damaged')]
    predictions = tuple(Prediction('ally', t, 'w', 10, 100, True)
                        for t in ('full', 'damaged'))
    assert choose_action(battle([ally, damaged, full], actions, predictions),
                         Policy()).target_id == 'damaged'


def test_healing_reserves_repairer_before_attacks():
    injured = unit('hurt', hp=69)
    healer = unit('healer', repair_capable=True, legal_repair_targets=('hurt',))
    repair = Action(ActionKind.REPAIR, 1, 'healer', 'hurt')
    assert choose_action(battle([injured, healer], [attack('enemy', actor='healer'), repair]),
                         Policy()) == repair


def test_unknown_observation_hands_over():
    assert choose_action(Snapshot(1), Policy()).kind is ActionKind.HANDOVER


def test_trust_resource_and_threshold_boundary():
    for hp, sp, expected in [(69, 10, ActionKind.TRUST), (70, 10, ActionKind.WAIT),
                              (69, 9, ActionKind.WAIT)]:
        hurt = unit('hurt', hp=hp)
        healer = unit('healer', trust_capable=True, sp=sp, trust_sp_cost=10,
                      legal_trust_targets=('hurt',), action_available=False)
        trust = Action(ActionKind.TRUST, 1, 'healer', 'hurt')
        wait = Action(ActionKind.WAIT, 1, 'hurt')
        result = choose_action(battle([hurt, healer], [trust, wait]), Policy())
        assert result.kind is expected


def test_post_heal_replans_and_never_reuses_reserved_action():
    hurt = unit('hurt', hp=69, legal_moves=((-1, 0),))
    healer = unit('healer', repair_capable=True, legal_repair_targets=('hurt',))
    repair = Action(ActionKind.REPAIR, 1, 'healer', 'hurt')
    before = battle([hurt, healer], [repair])
    assert choose_action(before, Policy()) == repair
    after = replace(before, sequence=2, units=(replace(hurt, hp=100),
                    replace(healer, action_available=False)),
                    legal_actions=(Action(ActionKind.WAIT, 2, 'hurt'),))
    assert choose_action(after, Policy()).kind is ActionKind.WAIT


def test_retreat_minimizes_exposure_and_does_not_attack():
    hurt = unit('hurt', hp=69, legal_moves=((-1, 0),))
    enemy = unit('enemy', Affiliation.ENEMY, position=(1, 0),
                 attack_positions=((0, 0), (0, 1)))
    move = Action(ActionKind.MOVE, 1, 'hurt', destination=(-1, 0))
    assert choose_action(battle([hurt, enemy], [attack('enemy', actor='hurt'), move]),
                         Policy()) == move


def test_retreat_unknown_reach_hands_over():
    hurt = unit('hurt', hp=69)
    enemy = unit('enemy', Affiliation.ENEMY)
    wait = Action(ActionKind.WAIT, 1, 'hurt')
    assert choose_action(battle([hurt, enemy], [wait]), Policy()).kind is ActionKind.HANDOVER


def test_no_improving_retreat_waits_and_never_ends_early():
    hurt = unit('hurt', hp=69)
    enemy = unit('enemy', Affiliation.ENEMY, position=(1, 0), attack_positions=())
    wait = Action(ActionKind.WAIT, 1, 'hurt')
    end = Action(ActionKind.END_TURN, 1)
    assert choose_action(battle([hurt, enemy], [end, wait]), Policy()) == wait


def test_end_turn_only_after_actions_exhausted():
    ally = unit('ally', action_available=False)
    end = Action(ActionKind.END_TURN, 1)
    assert choose_action(battle([ally], [end]), Policy()) == end
    assert choose_action(battle([replace(ally, action_available=True)], [end]),
                         Policy()).kind is ActionKind.HANDOVER


def test_weapon_boundaries_and_lower_median():
    for hp, expected in [(19, 'cheap'), (20, 'middle'), (90, 'middle'), (100, 'middle')]:
        weapons = (weapon('cheap', en_cost=0), weapon('middle', en_cost=10),
                   weapon('high', en_cost=20), weapon('highest', en_cost=30))
        ally = unit('ally', weapons=weapons)
        enemy = unit('enemy', Affiliation.ENEMY, hp)
        actions = [attack('enemy', w.id) for w in weapons]
        predictions = tuple(Prediction('ally', 'enemy', w.id, i * 10, 100, True)
                            for i, w in enumerate(weapons, 1))
        assert choose_action(battle([ally, enemy], actions, predictions),
                             Policy()).weapon_id == expected


def test_normalized_en_ammo_cost_and_zero_resources():
    en = weapon('en', en_cost=10)
    ammo = weapon('ammo', ammo_cost=1, ammo=2)
    ally = unit('ally', en=100, weapons=(en, ammo))
    enemy = unit('enemy', Affiliation.ENEMY, hp=10)
    actions = [attack('enemy', 'en'), attack('enemy', 'ammo')]
    predictions = tuple(Prediction('ally', 'enemy', w, 15, 100, True) for w in ('en', 'ammo'))
    snapshot = battle([ally, enemy], actions, predictions)
    assert choose_action(snapshot, Policy()).weapon_id == 'en'
    assert choose_action(replace(snapshot, units=(replace(ally, en=0), enemy)),
                         Policy()).weapon_id == 'ammo'


def test_boss_both_stats_common_counts_and_ambiguity():
    from psp_buddy.planner import is_boss
    common = tuple(replace(unit(f'c{i}', Affiliation.ENEMY), type_id='common',
                           max_hp=100 + i * 10, defense=10 + i * 10) for i in range(4))
    boss = unit('boss', Affiliation.ENEMY, max_hp=200, defense=50)
    assert is_boss(boss, (*common, boss), Policy())
    assert not is_boss(replace(boss, defense=20), (*common, boss), Policy())
    assert not is_boss(boss, (boss,), Policy())
    assert not is_boss(boss, (*common[:3], boss), Policy())
    assert not is_boss(boss, (replace(common[0], defense=None), *common[1:], boss), Policy())


def test_finishable_before_lower_hp_and_stable_tie():
    ally = unit('ally', weapons=(weapon(),))
    damaged = unit('damaged', Affiliation.ENEMY, hp=60)
    full = unit('full', Affiliation.ENEMY, hp=10)
    predictions = (Prediction('ally', 'damaged', 'w', 60, 100, True),
                   Prediction('ally', 'full', 'w', 1, 100, True))
    assert choose_action(battle([ally, damaged, full], [attack('full'), attack('damaged')],
                               predictions), Policy()).target_id == 'damaged'


def test_unknown_predictions_and_unsafe_weapons():
    ally = unit('ally', weapons=(weapon(),))
    enemy = unit('enemy', Affiliation.ENEMY)
    assert choose_action(battle([ally, enemy], [attack('enemy')]),
                         Policy()).kind is ActionKind.HANDOVER
    unsafe = replace(weapon(), map_attack=True)
    wait = Action(ActionKind.WAIT, 1, 'ally')
    assert choose_action(battle([replace(ally, weapons=(unsafe,)), enemy],
                               [attack('enemy'), wait]), Policy()) == wait


def test_unknown_enemy_hp_cannot_attack():
    ally = unit('ally', weapons=(weapon(),))
    enemy = unit('enemy', Affiliation.ENEMY, hp=None)
    prediction = Prediction('ally', 'enemy', 'w', 100, 100, True)
    assert choose_action(battle([ally, enemy], [attack('enemy')], (prediction,)),
                         Policy()).kind is ActionKind.HANDOVER


def test_move_requires_matching_legal_destination_evidence():
    ally = unit('ally', legal_moves=())
    enemy = unit('enemy', Affiliation.ENEMY, position=(5, 0))
    move = Action(ActionKind.MOVE, 1, 'ally', destination=(1, 0))
    assert choose_action(battle([ally, enemy], [move]), Policy()).kind is ActionKind.HANDOVER


def test_boss_weapon_90_boundary_and_strongest_above():
    common = tuple(replace(unit(f'c{i}', Affiliation.ENEMY), type_id='common',
                           defense=10) for i in range(4))
    weapons = (weapon('low'), weapon('medium'), weapon('high'))
    ally = unit('ally', weapons=weapons)
    for hp, expected in [(180, 'medium'), (181, 'high')]:
        enemy = unit('enemy', Affiliation.ENEMY, hp=hp, max_hp=200, defense=20)
        actions = [attack('enemy', w.id) for w in weapons]
        predictions = tuple(Prediction('ally', 'enemy', w.id, i * 10, 100, True)
                            for i, w in enumerate(weapons, 1))
        assert choose_action(battle([ally, enemy, *common], actions, predictions),
                             Policy()).weapon_id == expected


def test_cost_ties_prefer_damage_then_stable_weapon_identity():
    weapons = (weapon('z'), weapon('a'), weapon('weak'))
    ally = unit('ally', en=0, weapons=weapons)
    enemy = unit('enemy', Affiliation.ENEMY, hp=19)
    predictions = tuple(Prediction('ally', 'enemy', w.id,
                                  5 if w.id == 'weak' else 10, 100, True) for w in weapons)
    actions = [attack('enemy', w.id) for w in weapons]
    assert choose_action(battle([ally, enemy], actions, predictions), Policy()).weapon_id == 'a'


def test_unknown_sp_and_healing_legality_hand_over():
    hurt = unit('hurt', hp=69)
    healer = unit('healer', trust_capable=True, sp=None, trust_sp_cost=10,
                  legal_trust_targets=('hurt',), action_available=False)
    trust = Action(ActionKind.TRUST, 1, 'healer', 'hurt')
    assert choose_action(battle([hurt, healer], [trust]), Policy()).kind is ActionKind.HANDOVER
    healer = replace(healer, trust_capable=False, repair_capable=True,
                     action_available=True, legal_repair_targets=None)
    assert choose_action(battle([hurt, healer], [trust]), Policy()).kind is ActionKind.HANDOVER


def test_boss_baseline_uses_instance_medians_and_requires_strict_both_stats():
    from psp_buddy.planner import is_boss
    common = tuple(replace(unit(f'c{i}', Affiliation.ENEMY), type_id='common',
                           max_hp=hp, defense=defense)
                   for i, (hp, defense) in enumerate([(100, 10), (100, 10),
                                                      (300, 30), (300, 30)]))
    for hp, defense, expected in [(201, 21, True), (200, 21, False), (201, 20, False)]:
        rare = unit('rare', Affiliation.ENEMY, max_hp=hp, defense=defense)
        assert is_boss(rare, (*common, rare), Policy()) is expected


def test_movement_reobserves_before_attack_and_uses_preferred_enemy():
    ally = unit('ally', legal_moves=((1, 0), (0, 1)))
    damaged = unit('damaged', Affiliation.ENEMY, hp=90, position=(5, 0))
    full = unit('full', Affiliation.ENEMY, position=(0, 2))
    move = Action(ActionKind.MOVE, 1, 'ally', destination=(1, 0))
    other = Action(ActionKind.MOVE, 1, 'ally', destination=(0, 1))
    assert choose_action(battle([ally, damaged, full], [other, move]), Policy()) == move


def test_attack_after_move_requires_validated_post_move_capability():
    ally = unit('ally', weapons=(replace(weapon(), post_move=None),), legal_moves=((1, 0),))
    enemy = unit('enemy', Affiliation.ENEMY, position=(2, 0))
    action = replace(attack('enemy'), destination=(1, 0))
    prediction = Prediction('ally', 'enemy', 'w', 10, 100, True)
    assert choose_action(battle([ally, enemy], [action], (prediction,)),
                         Policy()).kind is ActionKind.HANDOVER


def test_combined_attack_returns_separate_move_before_replanning():
    ally = unit('ally', weapons=(weapon(),), legal_moves=((1, 0),))
    enemy = unit('enemy', Affiliation.ENEMY, position=(2, 0))
    combined = replace(attack('enemy'), destination=(1, 0))
    move = Action(ActionKind.MOVE, 1, 'ally', destination=(1, 0))
    prediction = Prediction('ally', 'enemy', 'w', 10, 100, True)
    assert choose_action(battle([ally, enemy], [combined, move], (prediction,)), Policy()) == move
    assert choose_action(battle([ally, enemy], [combined], (prediction,)),
                         Policy()).kind is ActionKind.HANDOVER


def test_unknown_fields_and_conflicting_predictions_fail_closed():
    ally = unit('ally', weapons=(weapon(),))
    enemy = unit('enemy', Affiliation.ENEMY)
    pred = Prediction('ally', 'enemy', 'w', 10, 100, True)
    snapshot = battle([ally, enemy], [attack('enemy')], (pred,))
    for changed in [replace(snapshot, units=None), replace(snapshot, legal_actions=None),
                    replace(snapshot, map_complete=None),
                    replace(snapshot, units=(replace(ally, weapons=None), enemy)),
                    replace(snapshot, predictions=(pred, replace(pred, damage=20)))]:
        assert choose_action(changed, Policy()).kind is ActionKind.HANDOVER


def test_available_second_ally_prevents_end_turn():
    first = unit('first', action_available=False)
    second = unit('second')
    wait = Action(ActionKind.WAIT, 1, 'second')
    assert choose_action(battle([first, second], [Action(ActionKind.END_TURN, 1), wait]),
                         Policy()) == wait


def test_multiple_destinations_do_not_weight_weapon_median():
    weapons = (weapon('low'), weapon('medium'), weapon('high'))
    ally = unit('ally', weapons=weapons, legal_moves=((1, 0), (0, 1)))
    enemy = unit('enemy', Affiliation.ENEMY, position=(2, 0))
    actions = [attack('enemy', 'low'),
               replace(attack('enemy', 'low'), destination=(1, 0)),
               replace(attack('enemy', 'low'), destination=(0, 1)),
               attack('enemy', 'medium'), attack('enemy', 'high')]
    predictions = tuple(Prediction('ally', 'enemy', w.id, i * 10, 100, True)
                        for i, w in enumerate(weapons, 1))
    assert choose_action(battle([ally, enemy], actions, predictions),
                         Policy()).weapon_id == 'medium'


def test_equal_target_priority_uses_stable_identity_for_reversed_input():
    weapons = (replace(weapon(), legal_target_ids=('a', 'z')),)
    ally = unit('ally', weapons=weapons)
    a = unit('a', Affiliation.ENEMY, hp=50, position=(2, 0))
    z = unit('z', Affiliation.ENEMY, hp=50, position=(0, 2))
    predictions = tuple(Prediction('ally', target, 'w', 10, 100, True)
                        for target in ('z', 'a'))
    for targets, actions in [([z, a], [attack('z'), attack('a')]),
                             ([a, z], [attack('a'), attack('z')])]:
        assert choose_action(battle([ally, *targets], actions, predictions),
                             Policy()).target_id == 'a'
