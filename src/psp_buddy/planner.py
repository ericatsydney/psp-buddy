"""One decision from one validated observation; no retained tactical state or inputs."""

from collections import Counter
from fractions import Fraction
from statistics import median

from .models import (
    Action,
    ActionKind,
    Affiliation,
    Phase,
    Policy,
    Position,
    Screen,
    Snapshot,
    Unit,
    ValidationStatus,
    Weapon,
)


class UnknownEvidence(ValueError):
    """A required tactical observation is unavailable."""


def _hp(unit: Unit) -> Fraction:
    if unit.hp is None or unit.max_hp is None:
        raise UnknownEvidence("unknown HP")
    return Fraction(unit.hp, unit.max_hp)


def _distance(first: Position | None, second: Position | None) -> int:
    if first is None or second is None:
        raise UnknownEvidence("unknown position")
    return abs(first[0] - second[0]) + abs(first[1] - second[1])


def is_boss(target: Unit, enemies: tuple[Unit, ...], policy: Policy) -> bool:
    counts = Counter(enemy.type_id for enemy in enemies)
    common = [enemy for enemy in enemies
              if counts[enemy.type_id] >= policy.common_type_min_count]
    if counts[target.type_id] >= policy.common_type_min_count or not common:
        return False
    if target.max_hp is None or target.defense is None:
        return False
    if any(enemy.max_hp is None or enemy.defense is None for enemy in common):
        return False
    hp = [enemy.max_hp for enemy in common if enemy.max_hp is not None]
    defense = [enemy.defense for enemy in common if enemy.defense is not None]
    return target.max_hp > median(hp) and target.defense > median(defense)


def _damage(snapshot: Snapshot, actor: Unit, target: Unit, weapon: Weapon) -> int:
    predictions = [p for p in (*snapshot.predictions, *weapon.predictions)
                   if (p.attacker_id, p.target_id, p.weapon_id)
                   == (actor.id, target.id, weapon.id)]
    if (not predictions or any(not p.validated or p.damage is None or p.damage < 0
                               for p in predictions)
            or len({p.damage for p in predictions}) != 1):
        raise UnknownEvidence("unknown or conflicting damage prediction")
    damage = predictions[0].damage
    assert damage is not None
    return damage


def _cost(actor: Unit, weapon: Weapon) -> Fraction | None:
    if weapon.map_attack is None or weapon.risks_allies is None:
        raise UnknownEvidence("unknown allied attack risk")
    if weapon.map_attack or weapon.risks_allies:
        return None
    if weapon.en_cost is None or weapon.ammo_cost is None:
        raise UnknownEvidence("unknown weapon cost")
    if weapon.en_cost < 0 or weapon.ammo_cost < 0:
        raise UnknownEvidence("invalid weapon cost")
    cost = Fraction(0)
    if weapon.en_cost:
        if actor.en is None or actor.en < 0:
            raise UnknownEvidence("unknown EN")
        if actor.en < weapon.en_cost:
            return None
        cost += Fraction(weapon.en_cost, actor.en)
    if weapon.ammo_cost:
        if weapon.ammo is None or weapon.ammo < 0:
            raise UnknownEvidence("unknown ammunition")
        if weapon.ammo < weapon.ammo_cost:
            return None
        cost += Fraction(weapon.ammo_cost, weapon.ammo)
    return cost


def _attacks(snapshot: Snapshot, actor: Unit, target: Unit,
             actions: tuple[Action, ...]) -> list[tuple[Action, int, Fraction]]:
    if actor.weapons is None:
        raise UnknownEvidence("unknown weapons")
    options = []
    for action in actions:
        if (action.kind is not ActionKind.ATTACK or action.actor_id != actor.id
                or action.target_id != target.id):
            continue
        weapon = next((w for w in actor.weapons if w.id == action.weapon_id), None)
        if weapon is None or weapon.legal_target_ids is None:
            raise UnknownEvidence("unknown legal weapon")
        if target.id not in weapon.legal_target_ids:
            raise UnknownEvidence("conflicting target legality")
        if action.destination is not None and action.destination != actor.position:
            if (weapon.post_move is not True or actor.legal_moves is None
                    or action.destination not in actor.legal_moves):
                raise UnknownEvidence("unknown or invalid post-move attack")
        cost = _cost(actor, weapon)
        if cost is not None:
            options.append((action, _damage(snapshot, actor, target, weapon), cost))
    # Destinations are action variants, not additional weapons in the median.
    # Prefer an attack from the current tile, then distance and coordinate ties.
    unique: dict[str, tuple[Action, int, Fraction]] = {}
    for option in sorted(options, key=lambda item: (
            item[0].destination not in (None, actor.position),
            _distance(item[0].destination or actor.position, target.position),
            item[0].destination or actor.position)):
        weapon_id = option[0].weapon_id
        assert weapon_id is not None
        unique.setdefault(weapon_id, option)
    return list(unique.values())


def _retreat(actor: Unit, enemies: tuple[Unit, ...], actions: tuple[Action, ...]) -> Action:
    if any(enemy.attack_positions is None for enemy in enemies):
        raise UnknownEvidence("unknown enemy attack reach")

    def safety(position: Position | None) -> tuple[int, int]:
        if position is None:
            raise UnknownEvidence("unknown retreat position")
        exposure = sum(position in (enemy.attack_positions or ()) for enemy in enemies)
        distance = min((_distance(position, enemy.position) for enemy in enemies), default=0)
        return (-exposure, distance)

    current = safety(actor.position)
    moves = [a for a in actions if a.kind is ActionKind.MOVE and a.actor_id == actor.id]
    improving = [a for a in moves if safety(a.destination) > current]
    if improving:
        return min(improving, key=lambda a: (-safety(a.destination)[0],
                                            -safety(a.destination)[1], a.destination))
    wait = next((a for a in actions if a.kind is ActionKind.WAIT and a.actor_id == actor.id), None)
    if wait is None:
        raise UnknownEvidence("no legal retreat or wait")
    return wait


def choose_action(snapshot: Snapshot, policy: Policy) -> Action:
    """Return a single current legal action. Caller must observe again after execution."""
    try:
        action = _choose(snapshot, policy)
        if action.kind is ActionKind.ATTACK and action.destination is not None:
            actor = next((u for u in snapshot.units or () if u.id == action.actor_id), None)
            if actor is not None and action.destination != actor.position:
                move = next((a for a in snapshot.legal_actions or ()
                             if a.kind is ActionKind.MOVE and a.actor_id == action.actor_id
                             and a.destination == action.destination), None)
                if move is None:
                    raise UnknownEvidence("move-and-attack needs separately legal movement")
                return move
        return action
    except UnknownEvidence as exc:
        return Action(ActionKind.HANDOVER, snapshot.sequence, reason=str(exc))


def _choose(snapshot: Snapshot, policy: Policy) -> Action:
    if (snapshot.validation is not ValidationStatus.VALIDATED
            or snapshot.phase is not Phase.PLAYER or snapshot.screen is not Screen.MAP
            or snapshot.units is None or snapshot.legal_actions is None
            or snapshot.map_complete is None):
        raise UnknownEvidence("unavailable validated player map")
    if snapshot.map_complete or snapshot.confirmed_defeated_ids:
        raise UnknownEvidence("map complete or confirmed defeat")
    units = snapshot.units
    if len({u.id for u in units}) != len(units):
        raise UnknownEvidence("duplicate unit identity")
    if any(u.affiliation is Affiliation.UNKNOWN or u.defeated is None
           or u.scripted_departure is None for u in units):
        raise UnknownEvidence("unknown roster state")
    live = tuple(u for u in units if not u.defeated and not u.scripted_departure)
    allies = tuple(sorted((u for u in live if u.affiliation is Affiliation.ALLY),
                          key=lambda u: u.id))
    enemies = tuple(u for u in live if u.affiliation is Affiliation.ENEMY)
    if any(u.defeated for u in units if u.affiliation is Affiliation.ALLY):
        raise UnknownEvidence("allied defeat")
    if any(u.action_available is None for u in allies):
        raise UnknownEvidence("unknown allied action availability")
    actions = snapshot.legal_actions
    if any(a.snapshot_sequence != snapshot.sequence for a in actions):
        raise UnknownEvidence("stale legal actions")
    for action in actions:
        if action.kind is ActionKind.MOVE:
            actor = next((u for u in allies if u.id == action.actor_id), None)
            if (actor is None or actor.legal_moves is None
                    or action.destination not in actor.legal_moves):
                raise UnknownEvidence("conflicting or unknown legal destination")
    injured = [u for u in allies if _hp(u) * 100 < policy.heal_below_percent]
    # Injury handling remains conservative; excluded support actions are never considered.
    for actor in allies:
        if not actor.action_available:
            continue
        if actor in injured:
            return _retreat(actor, enemies, actions)
        options = [(target, _attacks(snapshot, actor, target, actions)) for target in enemies]
        options = [(target, weapons) for target, weapons in options if weapons]
        if options:
            target, weapons = min(options, key=lambda pair: (
                _hp(pair[0]) == 1,
                not any(damage >= (pair[0].hp or 0) for _, damage, _ in pair[1]),
                _hp(pair[0]), _distance(actor.position, pair[0].position), pair[0].id))
            if not is_boss(target, enemies, policy) and _hp(target) * 100 \
                    < policy.cheap_weapon_below_percent:
                return min(weapons, key=lambda item: (item[2], -item[1],
                                                      item[0].weapon_id or ""))[0]
            if is_boss(target, enemies, policy) and _hp(target) * 100 \
                    > policy.strongest_boss_above_percent:
                return min(weapons, key=lambda item: (-item[1], item[0].weapon_id or ""))[0]
            weapons.sort(key=lambda item: (item[1], item[0].weapon_id or ""))
            return weapons[(len(weapons) - 1) // 2][0]
        if enemies:
            target = min(enemies, key=lambda e: (_hp(e) == 1, _hp(e),
                                                _distance(actor.position, e.position), e.id))
            moves = [a for a in actions if a.kind is ActionKind.MOVE and a.actor_id == actor.id
                     and _distance(a.destination, target.position)
                     < _distance(actor.position, target.position)]
            if moves:
                return min(moves, key=lambda a: (_distance(a.destination, target.position),
                                                a.destination))
        wait = next((a for a in actions if a.kind is ActionKind.WAIT and a.actor_id == actor.id),
                    None)
        if wait:
            return wait
        raise UnknownEvidence("available ally has no supported legal action")
    end = next((a for a in actions if a.kind is ActionKind.END_TURN), None)
    if end:
        return end
    raise UnknownEvidence("no legal end turn")
