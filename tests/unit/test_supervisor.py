import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

from psp_buddy.models import (
    Action,
    ActionKind,
    Affiliation,
    CheckpointReceipt,
    Phase,
    Policy,
    Prediction,
    Screen,
    Snapshot,
    Unit,
    ValidationStatus,
)
from psp_buddy.reactions import IncomingAttack
from psp_buddy.supervisor import BattleSupervisor


def battle(sequence=1, phase=Phase.PLAYER, screen=Screen.MAP, turn=1, **changes):
    return replace(Snapshot(sequence, "map", "game", "patch", f"frame-{sequence}", "profile",
                            ValidationStatus.VALIDATED, turn=turn, phase=phase, screen=screen,
                            units=(Unit("ally", "robot", Affiliation.ALLY, hp=100, max_hp=100,
                                        action_available=False, defeated=False,
                                        scripted_departure=False),),
                            legal_actions=(Action(ActionKind.END_TURN, sequence),),
                            map_complete=False, paused=False), **changes)


class Observer:
    def __init__(self, snapshots):
        self.snapshots = iter(snapshots)
    async def observe(self):
        return next(self.snapshots)


class Executor:
    def __init__(self, snapshots):
        self.snapshots = iter(snapshots)
        self.actions = []
        self.cleaned = False
    async def execute(self, action, before):
        self.actions.append(action)
        return next(self.snapshots)
    async def cleanup(self):
        self.cleaned = True
        return False


class Checkpoints:
    def __init__(self):
        self.current_snapshot = None
        self.receipt = None
        self.events = []
        self.saved_defeated_state = False
        self.fail_save = False
        self.fail_load = False
        self.reload_count = 0
        self.fail_initial = False
    def make_receipt(self, snapshot):
        return CheckpointReceipt(2, "game", "map", snapshot.sequence, "checkpoint",
                                 Path("state.ppst"), "0" * 64, True)
    async def verify_initial_checkpoint(self, snapshot, state_path):
        if self.fail_initial:
            raise ValueError("bad initial state")
        self.receipt = self.make_receipt(snapshot)
        self.current_snapshot = replace(snapshot, sequence=snapshot.sequence + 1,
                                        capture_id=f"frame-{snapshot.sequence + 1}",
                                        legal_actions=tuple(replace(a, snapshot_sequence=
                                            snapshot.sequence + 1) for a in snapshot.legal_actions))
        return self.receipt
    async def save_checkpoint(self, snapshot):
        self.events.append("save")
        if self.fail_save:
            raise ValueError("save failed")
        self.saved_defeated_state |= bool(snapshot.confirmed_defeated_ids)
        self.receipt = self.make_receipt(snapshot)
        self.current_snapshot = replace(snapshot, sequence=snapshot.sequence + 1,
                                        capture_id=f"frame-{snapshot.sequence + 1}",
                                        legal_actions=tuple(replace(a, snapshot_sequence=
                                            snapshot.sequence + 1) for a in snapshot.legal_actions))
        return self.receipt
    def can_end_turn(self, snapshot, receipt):
        return snapshot is self.current_snapshot and receipt is self.receipt
    async def load_checkpoint(self, receipt):
        if self.fail_load:
            raise ValueError("restore failed")
        self.reload_count += 1
        self.current_snapshot = battle(100 + self.reload_count * 100)
        return self.current_snapshot


def run(snapshots, outcomes, checkpoints=None, **options):
    executor = Executor(outcomes)
    checkpoints = checkpoints or Checkpoints()
    supervisor = BattleSupervisor(Observer(snapshots), executor, checkpoints,
                                  Policy(), Path("state.ppst"), **options)
    result = asyncio.run(supervisor.run())
    assert executor.cleaned
    return result, executor, checkpoints


def test_save_failure_prevents_end_turn():
    checkpoint = Checkpoints()
    checkpoint.fail_save = True
    result, executor, _ = run([battle()], [], checkpoint)
    assert result.reason == "checkpoint_save_failed"
    assert not executor.actions


def test_verified_save_precedes_end_turn_and_map_clear_handover():
    end = Action(ActionKind.END_TURN, 1)
    # Checkpoint observations replace legal action sequences as a real observer must.
    checkpoint = Checkpoints()
    original_save = checkpoint.save_checkpoint
    async def save(snapshot):
        receipt = await original_save(snapshot)
        current = checkpoint.current_snapshot
        checkpoint.current_snapshot = replace(current, legal_actions=(replace(end,
                                                   snapshot_sequence=current.sequence),))
        return receipt
    checkpoint.save_checkpoint = save
    result, executor, _ = run([battle()], [battle(4, map_complete=True, screen=Screen.MAP_CLEAR)],
                              checkpoint)
    assert result.reason == "map_complete"
    assert checkpoint.events == ["save"]
    assert [a.kind for a in executor.actions] == [ActionKind.END_TURN]


def test_initial_plus_three_failures_stops():
    checkpoint = Checkpoints()
    original_save = checkpoint.save_checkpoint
    async def save(snapshot):
        receipt = await original_save(snapshot)
        current = checkpoint.current_snapshot
        checkpoint.current_snapshot = replace(current, legal_actions=(Action(
            ActionKind.END_TURN, current.sequence),))
        return receipt
    checkpoint.save_checkpoint = save
    defeats = [battle(n, Phase.ENEMY, confirmed_defeated_ids=("ally",))
               for n in (4, 202, 302, 402)]
    result, executor, _ = run([battle()], defeats, checkpoint)
    assert result.reason == "retry_limit"
    assert result.retry_count == 3
    assert checkpoint.reload_count == 3
    assert checkpoint.saved_defeated_state is False
    assert all(action.kind is ActionKind.END_TURN for action in executor.actions)
    assert checkpoint.events == ["save"]


def test_failed_reload_does_not_consume_retry():
    checkpoint = Checkpoints()
    checkpoint.fail_load = True
    result, _, _ = run([battle()], [battle(4, Phase.ENEMY,
                      confirmed_defeated_ids=("ally",))], checkpoint)
    assert result.reason == "checkpoint_load_failed"
    assert result.retry_count == 0


@pytest.mark.parametrize("changes,reason", [
    (dict(screen=Screen.CHOICE), "unexpected_choice"),
    (dict(validation=ValidationStatus.PARTIAL), "invalid_observation"),
    (dict(screen=Screen.UNKNOWN), "unknown_screen"),
])
def test_invalid_startup_never_sends_input(changes, reason):
    result, executor, _ = run([battle(**changes)], [])
    assert result.reason == reason
    assert not executor.actions


def test_stop_releases_controls_without_checkpoint_requests():
    checkpoint = Checkpoints()
    result, executor, _ = run([battle()], [], checkpoint, stop_requested=lambda: True)
    assert result.reason == "user_stop"
    assert not executor.actions and not checkpoint.events


@pytest.mark.parametrize("reason", ["user_stop", "unknown_dialogue", "unexpected_choice"])
def test_executor_handover_reason_is_preserved(reason):
    from psp_buddy.executor import ExecutionError

    executor = Executor([])
    async def fail(action, before):
        raise ExecutionError(reason)
    executor.execute = fail
    supervisor = BattleSupervisor(Observer([battle()]), executor, Checkpoints(),
                                  Policy(), Path("state.ppst"))
    result = asyncio.run(supervisor.run())
    assert result.reason == reason
    assert executor.cleaned


def test_unknown_dialogue_not_skipped():
    result, executor, _ = run([battle(screen=Screen.DIALOGUE)], [])
    assert result.reason == "initial_checkpoint_failed"
    assert not executor.actions


def test_attempted_action_retained_when_connection_fails():
    executor = Executor([])
    async def fail(action, before):
        raise ConnectionError("offline disconnection")
    executor.execute = fail
    supervisor = BattleSupervisor(Observer([battle()]), executor, Checkpoints(),
                                  Policy(), Path("state.ppst"))
    result = asyncio.run(supervisor.run())
    assert result.reason == "connection_lost"
    assert [a.kind for a in result.history] == [ActionKind.END_TURN]
    assert executor.cleaned


def test_no_progress_after_input_hands_over():
    result, executor, _ = run([battle()], [battle(4)])
    assert result.reason == "no_progress"
    assert len(executor.actions) == 1


def test_unknown_roster_safety_blocks_startup():
    result, executor, _ = run([battle(units=(Unit("ally", "robot", Affiliation.ALLY,
                            hp=100, max_hp=100),))], [])
    assert result.reason == "invalid_observation"
    assert not executor.actions


def test_failed_reload_reports_affected_ally():
    checkpoint = Checkpoints()
    checkpoint.fail_load = True
    result, _, _ = run([battle()], [battle(4, Phase.ENEMY,
                      confirmed_defeated_ids=("ally",))], checkpoint)
    assert result.affected_unit_ids == ("ally",)


def test_scripted_departure_is_not_a_defeat():
    departed = Unit("departed", "robot", Affiliation.ALLY, hp=0, max_hp=100,
                    action_available=False, defeated=False, scripted_departure=True)
    outcome = battle(4, Phase.ENEMY, units=(*battle().units, departed),
                     scripted_departure_ids=("departed",))
    result, _, checkpoint = run([battle()], [outcome], max_observations=1)
    assert result.reason == "observation_budget"
    assert checkpoint.reload_count == 0


def test_stale_action_outcome_hands_over():
    result, executor, _ = run([battle()], [battle(3)])
    assert result.reason == "stale_observation"
    assert len(executor.actions) == 1


def test_cancellation_releases_controls():
    executor = Executor([])
    async def cancelled(action, before):
        raise asyncio.CancelledError
    executor.execute = cancelled
    supervisor = BattleSupervisor(Observer([battle()]), executor, Checkpoints(),
                                  Policy(), Path("state.ppst"))
    result = asyncio.run(supervisor.run())
    assert result.reason == "user_stop"
    assert executor.cleaned


def test_cleanup_failure_reports_unknown_pause():
    executor = Executor([])
    async def failed():
        raise ConnectionError("cleanup unavailable")
    executor.cleanup = failed
    supervisor = BattleSupervisor(Observer([battle()]), executor, Checkpoints(),
                                  Policy(), Path("state.ppst"), stop_requested=lambda: True)
    result = asyncio.run(supervisor.run())
    assert result.reason == "cleanup_failed"
    assert result.paused is None


def test_passive_enemy_observation_has_bounded_budget():
    result, executor, _ = run([battle(), battle(5, Phase.ENEMY)], [battle(4, Phase.ENEMY)],
                              max_observations=2)
    assert result.reason == "observation_budget"
    assert len(executor.actions) == 1


def test_action_budget_stops_before_second_input():
    result, executor, _ = run([battle(), battle(5, turn=2)], [battle(4, Phase.ENEMY)],
                              max_actions=1)
    assert result.reason == "action_budget"
    assert len(executor.actions) == 1


def test_disappeared_ally_without_departure_or_defeat_evidence_hands_over():
    outcome = battle(4, Phase.ENEMY, units=())
    result, executor, checkpoint = run([battle()], [outcome], max_observations=1)
    assert result.reason == "unresolved_roster"
    assert checkpoint.reload_count == 0 and len(executor.actions) == 1


def test_confirmed_defeat_of_disappeared_known_ally_reloads():
    outcome = battle(4, Phase.ENEMY, units=(), confirmed_defeated_ids=("ally",))
    result, _, checkpoint = run([battle()], [outcome], max_observations=2)
    assert result.reason == "observation_budget"
    assert checkpoint.reload_count == 1 and result.retry_count == 1


def test_unknown_hp_cannot_reset_retry_budget():
    checkpoint = Checkpoints()
    outcome = battle(202, turn=2, units=(replace(battle().units[0], hp=None),))
    result, _, _ = run([battle()], [battle(4, Phase.ENEMY,
                            confirmed_defeated_ids=("ally",)), outcome], checkpoint)
    assert result.reason == "invalid_observation"
    assert result.retry_count == 1


def test_reaction_advances_to_distinct_attack_even_without_stat_change():
    enemy = Unit("enemy", "robot", Affiliation.ENEMY, hp=100, max_hp=100,
                 defeated=False, scripted_departure=False)
    units = (*battle().units, enemy)
    def reaction(sequence):
        return battle(sequence, Phase.ENEMY, Screen.REACTION, units=units,
                      legal_actions=(Action(ActionKind.DEFEND, sequence, actor_id="ally"),))
    def incoming(snapshot, receipt):
        return IncomingAttack(receipt.checkpoint_id, snapshot.sequence, "map", 1,
                              "ally", "enemy", "attack", snapshot.sequence - 4,
                              Prediction("enemy", "ally", "attack", hit_rate=90,
                                         validated=True), validated=True)
    result, executor, _ = run([battle()], [reaction(4), reaction(5),
                            battle(6, map_complete=True, screen=Screen.MAP_CLEAR)],
                            incoming_attack=incoming)
    assert result.reason == "map_complete"
    assert [a.kind for a in executor.actions] == [ActionKind.END_TURN, ActionKind.DEFEND,
                                                 ActionKind.DEFEND]


def test_dialogue_advances_without_tactical_stat_change():
    def dialogue(sequence, content):
        return battle(sequence, Phase.TRANSITION, Screen.DIALOGUE, dialogue_id=content,
                      legal_actions=(Action(ActionKind.SKIP_DIALOGUE, sequence),))
    result, executor, _ = run([battle()], [dialogue(4, "first-line"),
                            dialogue(5, "second-line"),
                            battle(6, map_complete=True, screen=Screen.MAP_CLEAR)])
    assert result.reason == "map_complete"
    assert [a.kind for a in executor.actions] == [ActionKind.END_TURN, ActionKind.SKIP_DIALOGUE,
                                                 ActionKind.SKIP_DIALOGUE]


def test_map_clear_may_remove_roster_without_triggering_missing_ally():
    result, _, _ = run([battle()], [battle(4, units=(), map_complete=True,
                                          screen=Screen.MAP_CLEAR)])
    assert result.reason == "map_complete"


def test_same_dialogue_identity_does_not_establish_progress():
    def dialogue(sequence):
        return battle(sequence, Phase.TRANSITION, Screen.DIALOGUE, dialogue_id="same-line",
                      legal_actions=(Action(ActionKind.SKIP_DIALOGUE, sequence),))
    result, executor, _ = run([battle()], [dialogue(4), dialogue(5)])
    assert result.reason == "no_progress"
    assert len(executor.actions) == 2
