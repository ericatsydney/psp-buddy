"""Pure enemy reactions; adapters must supply current validated incoming-attack evidence.

Shared Snapshot has no attack occurrence or reaction-specific survival predictions.
IncomingAttack is the explicit adapter boundary, never reconstructed from an Action.
No emulator control, persistent state, model calls or retry accounting occurs here.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from .models import (
    Action,
    ActionKind,
    Affiliation,
    Phase,
    Policy,
    Prediction,
    Screen,
    Snapshot,
    ValidationStatus,
)


@dataclass(frozen=True)
class AttackKey:
    checkpoint_id: str
    map_id: str
    turn: int
    ally_id: str
    attacker_id: str
    weapon_id: str
    occurrence: int


@dataclass(frozen=True)
class ReactionEstimate:
    kind: ActionKind
    weapon_id: str | None
    survival_basis_points: int | None
    validated: bool = False


@dataclass(frozen=True)
class IncomingAttack:
    checkpoint_id: str
    snapshot_sequence: int
    map_id: str
    turn: int
    ally_id: str
    attacker_id: str
    weapon_id: str
    occurrence: int
    prediction: Prediction
    estimates: tuple[ReactionEstimate, ...] = ()
    validated: bool = False

    @property
    def key(self) -> AttackKey:
        return AttackKey(self.checkpoint_id, self.map_id, self.turn, self.ally_id,
                         self.attacker_id, self.weapon_id, self.occurrence)


@dataclass(frozen=True)
class FailedReaction:
    """A reaction from a confirmed failed attempt, keyed across checkpoint reloads."""

    context: AttackKey
    kind: ActionKind
    weapon_id: str | None = None


def choose_reaction(
    snapshot: Snapshot, policy: Policy, attempt: int,
    history: Sequence[FailedReaction] | Sequence[Action], *,
    incoming: IncomingAttack | None = None,
) -> Action:
    def handover(reason: str = 'unknown_reaction_evidence') -> Action:
        return Action(ActionKind.HANDOVER, snapshot.sequence, reason=reason)

    if type(attempt) is not int or not 0 <= attempt <= policy.max_retries:
        return handover('retry_limit')
    if any(type(value) is not int or not 0 <= value <= 100 for value in (
        policy.defend_above_hit_percent, policy.evade_below_percent,
    )):
        return handover()
    if (incoming is None or incoming.validated is not True
            or snapshot.validation is not ValidationStatus.VALIDATED
            or snapshot.phase is not Phase.ENEMY or snapshot.screen is not Screen.REACTION
            or snapshot.map_complete is not False or snapshot.confirmed_defeated_ids
            or snapshot.units is None or snapshot.legal_actions is None
            or type(incoming.snapshot_sequence) is not int
            or incoming.snapshot_sequence != snapshot.sequence
            or incoming.map_id != snapshot.map_id or incoming.turn != snapshot.turn
            or type(incoming.turn) is not int or incoming.turn < 0
            or type(incoming.occurrence) is not int or incoming.occurrence < 0
            or not all((incoming.checkpoint_id, incoming.ally_id,
                        incoming.attacker_id, incoming.weapon_id))):
        return handover()
    prediction = incoming.prediction
    if (prediction.validated is not True
            or (prediction.attacker_id, prediction.target_id, prediction.weapon_id)
            != (incoming.attacker_id, incoming.ally_id, incoming.weapon_id)
            or type(prediction.hit_rate) is not int or not 0 <= prediction.hit_rate <= 100):
        return handover()
    if any(u.affiliation is Affiliation.ALLY and (u.defeated is True
           or (u.hp == 0 and u.scripted_departure is not True))
           for u in snapshot.units):
        return handover('allied_defeat')
    allies = [u for u in snapshot.units if u.id == incoming.ally_id]
    attackers = [u for u in snapshot.units if u.id == incoming.attacker_id]
    if (len(allies) != 1 or len(attackers) != 1
            or allies[0].affiliation is not Affiliation.ALLY
            or attackers[0].affiliation is not Affiliation.ENEMY):
        return handover()
    ally = allies[0]
    if (ally.hp is None or ally.max_hp is None or ally.hp <= 0
            or ally.defeated is not False or ally.scripted_departure is not False
            or incoming.ally_id in snapshot.scripted_departure_ids):
        return handover()
    actions = [a for a in snapshot.legal_actions
               if a.kind in (ActionKind.DEFEND, ActionKind.EVADE, ActionKind.COUNTER)
               and a.actor_id == incoming.ally_id]
    if not actions or len({(a.kind, a.weapon_id) for a in actions}) != len(actions):
        return handover()
    for action in actions:
        if (action.destination is not None
                or (action.kind is ActionKind.COUNTER
                    and (action.target_id != incoming.attacker_id or not action.weapon_id))
                or (action.kind is not ActionKind.COUNTER
                    and (action.weapon_id is not None or action.target_id is not None))):
            return handover()
    if any(not isinstance(failed, FailedReaction)
           or failed.kind not in (ActionKind.DEFEND, ActionKind.EVADE, ActionKind.COUNTER)
           or (failed.kind is ActionKind.COUNTER and not failed.weapon_id)
           or (failed.kind is not ActionKind.COUNTER and failed.weapon_id is not None)
           for failed in history):
        return handover()
    if attempt == 0:
        if prediction.hit_rate > policy.defend_above_hit_percent:
            kind = ActionKind.DEFEND
        elif 100 * ally.hp < policy.evade_below_percent * ally.max_hp:
            kind = ActionKind.EVADE
        elif any(a.kind is ActionKind.COUNTER for a in actions):
            kind = ActionKind.COUNTER
        else:
            kind = ActionKind.DEFEND
        candidates = [a for a in actions if a.kind is kind]
        return min(candidates, key=lambda a: a.weapon_id or '') if candidates else handover()

    failed_choices = {(f.kind, f.weapon_id) for f in history
                      if isinstance(f, FailedReaction) and f.context == incoming.key}
    candidates = [a for a in actions if (a.kind, a.weapon_id) not in failed_choices]
    if not candidates:
        return handover('no_distinct_reaction')
    estimates: dict[tuple[ActionKind, str | None], int] = {}
    for estimate in incoming.estimates:
        key = (estimate.kind, estimate.weapon_id)
        survival = estimate.survival_basis_points
        if (key in estimates or estimate.validated is not True
                or type(survival) is not int or not 0 <= survival <= 10000):
            return handover()
        estimates[key] = survival
    if any((a.kind, a.weapon_id) not in estimates for a in candidates):
        return handover()
    profiles = (
        (ActionKind.DEFEND, ActionKind.EVADE, ActionKind.COUNTER),
        (ActionKind.EVADE, ActionKind.DEFEND, ActionKind.COUNTER),
        (ActionKind.COUNTER, ActionKind.DEFEND, ActionKind.EVADE),
    )
    priority = profiles[attempt - 1]
    return min(candidates, key=lambda a: (
        -estimates[(a.kind, a.weapon_id)], priority.index(a.kind), a.weapon_id or '',
    ))
