from dataclasses import FrozenInstanceError

import pytest


def test_unknown_resources_remain_unknown_and_unit_is_immutable() -> None:
    from psp_buddy.models import Affiliation, Unit

    unit = Unit(id="ally", type_id="robot", affiliation=Affiliation.ALLY)
    assert unit.hp is None
    assert unit.max_hp is None
    assert unit.en is None
    with pytest.raises(FrozenInstanceError):
        unit.hp = 0


def test_snapshot_cannot_claim_validated_with_unknown_identity() -> None:
    from psp_buddy.models import Snapshot, ValidationStatus

    with pytest.raises(ValueError, match="identity"):
        Snapshot(sequence=1, validation=ValidationStatus.VALIDATED)


def test_action_requires_current_observation_sequence() -> None:
    from psp_buddy.models import Action, ActionKind

    with pytest.raises(ValueError, match="sequence"):
        Action(kind=ActionKind.WAIT, snapshot_sequence=-1)


def test_unknown_maximum_hp_never_becomes_zero() -> None:
    from psp_buddy.models import Affiliation, Unit

    unit = Unit(id="u", type_id="t", affiliation=Affiliation.ALLY, hp=50)
    assert unit.max_hp is None
    with pytest.raises(ValueError, match="HP"):
        Unit(id="u", type_id="t", affiliation=Affiliation.ALLY, hp=51, max_hp=50)


def test_snapshot_rejects_stale_legal_action_evidence() -> None:
    from psp_buddy.models import Action, ActionKind, Snapshot

    stale = Action(kind=ActionKind.WAIT, snapshot_sequence=1)
    with pytest.raises(ValueError, match="stale"):
        Snapshot(sequence=2, legal_actions=(stale,))


def test_policy_rejects_retry_budget_above_three() -> None:
    from psp_buddy.models import Policy

    with pytest.raises(ValueError, match="retries"):
        Policy(max_retries=4)


@pytest.mark.parametrize("dialogue_id", ["", " ", 1])
def test_dialogue_identity_is_unknown_or_nonempty_text(dialogue_id) -> None:
    from psp_buddy.models import Snapshot

    with pytest.raises(ValueError, match="dialogue"):
        Snapshot(sequence=1, dialogue_id=dialogue_id)


def test_unknown_collections_differ_from_observed_empty_collections() -> None:
    from psp_buddy.models import Affiliation, Snapshot, Unit

    unknown = Unit(id="u", type_id="t", affiliation=Affiliation.ALLY)
    empty = Unit(id="u", type_id="t", affiliation=Affiliation.ALLY, weapons=())
    assert unknown.weapons is None
    assert empty.weapons == ()
    assert Snapshot(sequence=0).units is None
    assert Snapshot(sequence=0, units=()).units == ()


def test_enemy_attack_positions_preserve_unknown_and_known_empty() -> None:
    from psp_buddy.models import Affiliation, Unit

    unknown = Unit(id="enemy", type_id="robot", affiliation=Affiliation.ENEMY)
    assert unknown.attack_positions is None
    empty = Unit(
        id="enemy", type_id="robot", affiliation=Affiliation.ENEMY, attack_positions=()
    )
    assert empty.attack_positions == ()
