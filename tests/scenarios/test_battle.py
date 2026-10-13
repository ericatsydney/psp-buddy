"""Synthetic full orchestration with actual checkpoint/reaction services; no emulator."""

import asyncio
import hashlib
from dataclasses import replace
from pathlib import Path

from psp_buddy.checkpoint import (
    CheckpointCompletion,
    StateArtifact,
    VerifiedCheckpointService,
    checkpoint_state_fingerprint,
)
from psp_buddy.executor import (
    ActionRecipe,
    ActionSelection,
    BoundedExecutor,
    ExecutionObservation,
    ExpectedContext,
    RecipeBinding,
    RecipeStep,
)
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
from psp_buddy.reactions import IncomingAttack, ReactionEstimate
from psp_buddy.supervisor import BattleSupervisor


class World:
    def __init__(self, state_path: Path):
        self.path = state_path
        self.ally = Unit("ally", "robot", Affiliation.ALLY, position=(0, 0), hp=100,
                         max_hp=100, action_available=True, defeated=False,
                         scripted_departure=False, legal_moves=(), weapons=())
        self.enemy = Unit("enemy", "enemy-type", Affiliation.ENEMY, position=(9, 9),
                          hp=100, max_hp=100, defeated=False, scripted_departure=False)
        self.snapshot = Snapshot(1, "map", "game", "patch", "frame-1", "profile",
                                 ValidationStatus.VALIDATED, turn=1, phase=Phase.PLAYER,
                                 screen=Screen.MAP, units=(self.ally, self.enemy),
                                 legal_actions=(Action(ActionKind.WAIT, 1, actor_id="ally"),),
                                 map_complete=False, paused=False)
        self.saved = self.snapshot
        self.write_state()
        self.operation = ""
        self.events = []
        self.failed_once = False
        self.cleaned = False

    def advance(self, **changes):
        sequence = self.snapshot.sequence + 1
        actions = changes.pop("legal_actions", self.snapshot.legal_actions)
        self.snapshot = replace(self.snapshot, sequence=sequence, capture_id=f"frame-{sequence}",
                                legal_actions=tuple(replace(a, snapshot_sequence=sequence)
                                                    for a in actions), **changes)
        return self.snapshot

    def write_state(self):
        self.path.write_bytes(checkpoint_state_fingerprint(self.saved).encode("ascii"))

    async def observe(self):
        return self.advance()

    async def request_save(self, slot):
        self.events.append(("save", slot))
        self.saved = self.snapshot
        self.write_state()
        self.operation = "save"
        return "save-request"

    async def request_load(self, slot):
        self.events.append(("load", slot))
        sequence = self.snapshot.sequence
        self.snapshot = replace(self.saved, sequence=sequence, capture_id=f"frame-{sequence}",
                                legal_actions=tuple(replace(a, snapshot_sequence=sequence)
                                                    for a in self.saved.legal_actions))
        self.operation = "load"
        return "load-request"

    async def wait_complete(self, request_id):
        return CheckpointCompletion(request_id, self.operation, 2, "game", "map", True,
                                    f"checkpoint-turn-{self.saved.turn}", self.path)

    async def inspect_state(self, path):
        data = path.read_bytes()
        return StateArtifact(2, "game", "map", f"checkpoint-turn-{self.saved.turn}", len(data),
                             hashlib.sha256(data).hexdigest(), True,
                             checkpoint_state_fingerprint(self.saved))

    def incoming(self, snapshot, receipt):
        return IncomingAttack(receipt.checkpoint_id, snapshot.sequence, "map", snapshot.turn,
                              "ally", "enemy", "enemy-weapon", 0,
                              Prediction("enemy", "ally", "enemy-weapon", hit_rate=81,
                                         validated=True),
                              (ReactionEstimate(ActionKind.DEFEND, None, 9500, True),
                               ReactionEstimate(ActionKind.EVADE, None, 9000, True)), True)

    async def execute(self, action, before):
        assert before is self.snapshot
        assert action in before.legal_actions
        self.events.append((action.kind.value, before.turn))
        if action.kind is ActionKind.WAIT:
            self.ally = replace(self.ally, action_available=False)
            return self.advance(units=(self.ally, self.enemy),
                                legal_actions=(Action(ActionKind.END_TURN, 0),))
        if action.kind is ActionKind.END_TURN:
            return self.advance(phase=Phase.ENEMY, screen=Screen.REACTION,
                                legal_actions=(Action(ActionKind.DEFEND, 0, actor_id="ally"),
                                               Action(ActionKind.EVADE, 0, actor_id="ally")))
        if action.kind in (ActionKind.DEFEND, ActionKind.EVADE):
            if not self.failed_once:
                self.failed_once = True
                return self.advance(screen=Screen.MAP, confirmed_defeated_ids=("ally",),
                                    legal_actions=())
            if before.turn == 1:
                self.ally = replace(self.ally, action_available=True)
                return self.advance(turn=2, phase=Phase.PLAYER, screen=Screen.MAP,
                                    units=(self.ally, self.enemy), legal_actions=(
                                        Action(ActionKind.WAIT, 0, actor_id="ally"),))
            return self.advance(screen=Screen.MAP_CLEAR, map_complete=True, legal_actions=())
        raise AssertionError(action)

    async def cleanup(self):
        self.cleaned = True
        return False


def test_two_turn_battle_retries_reactions_without_replaying_allied_actions(tmp_path):
    world = World(tmp_path / "working.ppst")
    checkpoint = VerifiedCheckpointService(2, "game", "map", world, state_root=tmp_path)
    supervisor = BattleSupervisor(world, world, checkpoint, Policy(), world.path,
                                  incoming_attack=world.incoming, max_actions=20,
                                  max_observations=30)
    result = asyncio.run(supervisor.run())
    assert result.reason == "map_complete"
    assert result.retry_count == 0  # The successful enemy phase reset the retry budget.
    assert world.cleaned and result.paused is False
    assert world.events == [
        ("wait", 1), ("save", 2), ("end_turn", 1), ("defend", 1), ("load", 2),
        ("end_turn", 1), ("evade", 1), ("wait", 2), ("save", 2),
        ("end_turn", 2), ("defend", 2),
    ]
    assert result.checkpoint.slot == 2
    assert len(result.history) == 8


class MenuWorldAdapter:
    """Synthetic calibrated contexts, not actual PSP menu commands or recognition."""

    def __init__(self, world):
        self.world = world
        self.selection = None
        self.release_count = 0

    async def observe(self):
        snapshot = await self.world.observe()
        return ExecutionObservation(snapshot, snapshot.screen.value, self.selection,
                                    "synthetic-reviewed-menu", True,
                                    attack_context_id=(f"turn-{snapshot.turn}-attack-0"
                                                       if snapshot.screen is Screen.REACTION
                                                       else None))

    async def send(self, command):
        kind = ActionKind(command.removeprefix("synthetic:"))
        action = next(a for a in self.world.snapshot.legal_actions if a.kind is kind)
        await self.world.execute(action, self.world.snapshot)
        self.selection = None

    async def release_all(self):
        self.release_count += 1
        self.world.cleaned = True
        return False

    def recipes(self, action, before):
        self.selection = ActionSelection.from_action(action)
        context = ExpectedContext(before.screen, before.phase, before.screen.value,
                                  self.selection,
                                  attack_context_id=(f"turn-{before.turn}-attack-0"
                                                     if before.screen is Screen.REACTION else None))
        if action.kind is ActionKind.WAIT:
            screen, phase = Screen.MAP, Phase.PLAYER
        elif action.kind is ActionKind.END_TURN:
            screen, phase = Screen.REACTION, Phase.ENEMY
        elif not self.world.failed_once:
            screen, phase = Screen.MAP, Phase.ENEMY
        elif before.turn == 1:
            screen, phase = Screen.MAP, Phase.PLAYER
        else:
            screen, phase = Screen.MAP_CLEAR, Phase.ENEMY
        expected = ExpectedContext(screen, phase, screen.value, None,
                                   attack_context_id=(f"turn-{before.turn}-attack-0"
                                                      if screen is Screen.REACTION else None))
        def step_postcondition(first, after, planned):
            return after.snapshot.screen is screen and after.snapshot.phase is phase
        def final_postcondition(first, after, planned):
            if planned.kind is ActionKind.WAIT:
                return after.units[0].action_available is False
            if planned.kind is ActionKind.END_TURN:
                return after.phase is Phase.ENEMY and after.screen is Screen.REACTION
            return (bool(after.confirmed_defeated_ids) or after.map_complete is True
                    or after.phase is Phase.PLAYER and after.turn > first.turn)
        step = RecipeStep(f"synthetic:{action.kind.value}", context, expected,
                          "synthetic-reviewed-step", step_postcondition)
        return ActionRecipe(action, RecipeBinding.from_snapshot(before), (step,),
                            "synthetic-reviewed-recipe", True, final_postcondition)


def test_actual_bounded_executor_composes_with_checkpoint_retries_and_supervisor(tmp_path):
    world = World(tmp_path / "working.ppst")
    adapter = MenuWorldAdapter(world)
    executor = BoundedExecutor(adapter, adapter.recipes)
    checkpoint = VerifiedCheckpointService(2, "game", "map", world, state_root=tmp_path)
    supervisor = BattleSupervisor(world, executor, checkpoint, Policy(), world.path,
                                  incoming_attack=world.incoming, max_actions=20,
                                  max_observations=30)
    result = asyncio.run(supervisor.run())
    assert result.reason == "map_complete"
    assert result.retry_count == 0
    assert len(result.history) == 8
    assert adapter.release_count == 9  # Every action plus final supervisor cleanup.
    assert world.events == [
        ("wait", 1), ("save", 2), ("end_turn", 1), ("defend", 1), ("load", 2),
        ("end_turn", 1), ("evade", 1), ("wait", 2), ("save", 2),
        ("end_turn", 2), ("defend", 2),
    ]
