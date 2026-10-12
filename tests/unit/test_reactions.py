from dataclasses import replace

import pytest

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
)
from psp_buddy.reactions import (
    FailedReaction,
    IncomingAttack,
    ReactionEstimate,
    choose_reaction,
)


def observation(hp=60, hit=70, kinds=(ActionKind.DEFEND, ActionKind.EVADE, ActionKind.COUNTER)):
    actions = tuple(Action(k, 1, 'ally', 'enemy' if k is ActionKind.COUNTER else None,
                           'counter' if k is ActionKind.COUNTER else None) for k in kinds)
    snapshot = Snapshot(1, 'map', 'game', 'patch', 'capture', 'profile',
                        ValidationStatus.VALIDATED, 2, Phase.ENEMY, Screen.REACTION,
                        units=(Unit('ally', 'robot', Affiliation.ALLY, hp=hp, max_hp=100,
                                    defeated=False, scripted_departure=False),
                               Unit('enemy', 'robot', Affiliation.ENEMY, hp=100, max_hp=100)),
                        legal_actions=actions, map_complete=False)
    incoming = IncomingAttack('checkpoint', 1, 'map', 2, 'ally', 'enemy', 'attack', 0,
                              Prediction('enemy', 'ally', 'attack', 20, hit, True),
                              tuple(ReactionEstimate(a.kind, a.weapon_id, 9000, True)
                                    for a in actions), True)
    return snapshot, incoming


def decide(snapshot, incoming, attempt=0, history=()):
    return choose_reaction(snapshot, Policy(), attempt, history, incoming=incoming)


def test_missing_incoming_attack_hands_over():
    action = choose_reaction(Snapshot(1), Policy(), 0, ())
    assert action.kind is ActionKind.HANDOVER
    assert action.reason == 'unknown_reaction_evidence'


@pytest.mark.parametrize('hp,hit,expected', [
    (40, 81, ActionKind.DEFEND), (49, 80, ActionKind.EVADE),
    (50, 80, ActionKind.COUNTER), (50, 81, ActionKind.DEFEND),
])
def test_initial_priority_and_strict_boundaries(hp, hit, expected):
    snapshot, incoming = observation(hp, hit)
    assert decide(snapshot, incoming).kind is expected


def test_no_counter_falls_back_to_defend():
    snapshot, incoming = observation(kinds=(ActionKind.DEFEND, ActionKind.EVADE))
    assert decide(snapshot, incoming).kind is ActionKind.DEFEND


def test_scripted_departed_other_ally_is_not_a_defeat():
    snapshot, incoming = observation()
    departed = Unit('departed', 'robot', Affiliation.ALLY, hp=0, max_hp=100,
                    defeated=False, scripted_departure=True)
    snapshot = replace(snapshot, units=(*snapshot.units, departed),
                       scripted_departure_ids=('departed',))
    assert decide(snapshot, incoming).kind is ActionKind.COUNTER


def test_required_priority_unavailable_hands_over():
    snapshot, incoming = observation(40, 81, (ActionKind.EVADE,))
    assert decide(snapshot, incoming).kind is ActionKind.HANDOVER


@pytest.mark.parametrize('attempt,expected', [
    (1, ActionKind.DEFEND), (2, ActionKind.EVADE), (3, ActionKind.COUNTER),
])
def test_retry_profiles_are_bounded_deterministic(attempt, expected):
    snapshot, incoming = observation()
    assert decide(snapshot, incoming, attempt).kind is expected
    assert decide(snapshot, incoming, attempt) == decide(snapshot, incoming, attempt)


def test_retry_survival_estimates_override_profile_priority():
    snapshot, incoming = observation()
    incoming = replace(incoming, estimates=(
        ReactionEstimate(ActionKind.DEFEND, None, 2000, True),
        ReactionEstimate(ActionKind.EVADE, None, 5000, True),
        ReactionEstimate(ActionKind.COUNTER, 'counter', 9500, True)))
    assert decide(snapshot, incoming, 1).kind is ActionKind.COUNTER


def test_failed_identical_choice_is_excluded():
    snapshot, incoming = observation()
    failed = FailedReaction(incoming.key, ActionKind.DEFEND)
    assert decide(snapshot, incoming, 1, (failed,)).kind is ActionKind.EVADE


def test_exhausted_distinct_choices_hands_over():
    snapshot, incoming = observation(kinds=(ActionKind.DEFEND,))
    failed = FailedReaction(incoming.key, ActionKind.DEFEND)
    assert decide(snapshot, incoming, 1, (failed,)).reason == 'no_distinct_reaction'


@pytest.mark.parametrize('field,value', [('occurrence', 1), ('weapon_id', 'other'),
    ('attacker_id', 'other'), ('ally_id', 'other'), ('checkpoint_id', 'other')])
def test_history_key_distinguishes_attack_context(field, value):
    snapshot, incoming = observation()
    failed = FailedReaction(replace(incoming, **{field: value}).key, ActionKind.DEFEND)
    assert decide(snapshot, incoming, 1, (failed,)).kind is ActionKind.DEFEND


@pytest.mark.parametrize('change', [
    {'validated': False}, {'snapshot_sequence': 0}, {'map_id': 'other'},
    {'turn': 1}, {'occurrence': -1}, {'checkpoint_id': ''},
    {'prediction': Prediction('enemy', 'ally', 'attack', 20, None, True)},
    {'prediction': Prediction('enemy', 'ally', 'attack', 20, 101, True)},
    {'prediction': Prediction('other', 'ally', 'attack', 20, 50, True)},
])
def test_unknown_or_mismatched_context_hands_over(change):
    snapshot, incoming = observation()
    assert decide(snapshot, replace(incoming, **change)).kind is ActionKind.HANDOVER


@pytest.mark.parametrize('change', [
    {'validation': ValidationStatus.PARTIAL}, {'phase': Phase.PLAYER},
    {'screen': Screen.MAP}, {'units': None}, {'legal_actions': None},
    {'map_complete': True}, {'confirmed_defeated_ids': ('ally',)},
])
def test_invalid_snapshot_hands_over(change):
    snapshot, incoming = observation()
    assert decide(replace(snapshot, **change), incoming).kind is ActionKind.HANDOVER


@pytest.mark.parametrize('estimates', [(),
    (ReactionEstimate(ActionKind.DEFEND, None, None, True),),
    (ReactionEstimate(ActionKind.DEFEND, None, 10001, True),),
    (ReactionEstimate(ActionKind.DEFEND, None, 9000, False),)])
def test_retry_requires_complete_validated_survival_estimates(estimates):
    snapshot, incoming = observation()
    assert decide(snapshot, replace(incoming, estimates=estimates), 1).kind is ActionKind.HANDOVER


@pytest.mark.parametrize('attempt', [-1, 4, True])
def test_invalid_attempt_hands_over(attempt):
    snapshot, incoming = observation()
    assert decide(snapshot, incoming, attempt).reason == 'retry_limit'


def test_uncontextualized_history_fails_closed():
    snapshot, incoming = observation()
    assert decide(snapshot, incoming, 1, (snapshot.legal_actions[0],)).kind is ActionKind.HANDOVER

@pytest.mark.parametrize('hit', [True, -1, 101])
def test_invalid_hit_rate_hands_over(hit):
    snapshot, incoming = observation(hit=hit)
    assert decide(snapshot, incoming).kind is ActionKind.HANDOVER


def test_conflicting_survival_estimates_hands_over():
    snapshot, incoming = observation()
    incoming = replace(incoming, estimates=incoming.estimates + (
        ReactionEstimate(ActionKind.DEFEND, None, 8000, True),))
    assert decide(snapshot, incoming, 1).kind is ActionKind.HANDOVER


def test_unknown_ally_hp_hands_over():
    snapshot, incoming = observation()
    snapshot = replace(snapshot, units=(replace(snapshot.units[0], hp=None), snapshot.units[1]))
    assert decide(snapshot, incoming).kind is ActionKind.HANDOVER


def test_duplicate_identity_hands_over():
    snapshot, incoming = observation()
    snapshot = replace(snapshot, units=snapshot.units + (snapshot.units[0],))
    assert decide(snapshot, incoming).kind is ActionKind.HANDOVER


def test_counter_for_wrong_attacker_hands_over():
    snapshot, incoming = observation()
    actions = tuple(replace(a, target_id='other') if a.kind is ActionKind.COUNTER else a
                    for a in snapshot.legal_actions)
    assert decide(replace(snapshot, legal_actions=actions), incoming).kind is ActionKind.HANDOVER


def test_failed_history_must_contain_reaction_choices():
    snapshot, incoming = observation()
    failed = FailedReaction(incoming.key, ActionKind.WAIT)
    assert decide(snapshot, incoming, 1, (failed,)).kind is ActionKind.HANDOVER


def test_boolean_context_sequence_hands_over():
    snapshot, incoming = observation()
    assert decide(snapshot, replace(incoming, snapshot_sequence=True)).kind is ActionKind.HANDOVER


@pytest.mark.parametrize('policy', [Policy(defend_above_hit_percent=101),
    Policy(evade_below_percent=-1), Policy(defend_above_hit_percent=True)])
def test_invalid_policy_thresholds_handover(policy):
    snapshot, incoming = observation()
    assert choose_reaction(snapshot, policy, 0, (), incoming=incoming).kind is ActionKind.HANDOVER


def test_any_authoritative_allied_defeat_stops_reaction():
    snapshot, incoming = observation()
    fallen = Unit('fallen', 'robot', Affiliation.ALLY, hp=0, max_hp=100, defeated=True)
    assert decide(replace(snapshot, units=snapshot.units + (fallen,)), incoming).kind \
        is ActionKind.HANDOVER


@pytest.mark.parametrize('changes', [dict(defeated=None), dict(scripted_departure=None)])
def test_target_safety_must_be_known(changes):
    snapshot, incoming = observation()
    snapshot = replace(snapshot, units=(replace(snapshot.units[0], **changes), snapshot.units[1]))
    assert decide(snapshot, incoming).kind is ActionKind.HANDOVER
