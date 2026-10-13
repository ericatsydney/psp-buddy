"""Bounded offline orchestration; live observation/execution adapters remain gated."""

import asyncio
import math
from collections.abc import Awaitable, Callable
from enum import Enum
from pathlib import Path
from typing import Protocol, TypeVar

from .checkpoint import checkpoint_state_fingerprint
from .executor import ExecutionError
from .models import (
    Action,
    ActionKind,
    Affiliation,
    CheckpointReceipt,
    Handover,
    Observer,
    Phase,
    Policy,
    Screen,
    Snapshot,
    ValidationStatus,
)
from .planner import choose_action
from .reactions import FailedReaction, IncomingAttack, choose_reaction

T = TypeVar("T")


class SupervisorState(Enum):
    STARTUP = "startup"
    PLAYER_PHASE = "player_phase"
    CHECKPOINT_SAVE = "checkpoint_save"
    ENEMY_PHASE = "enemy_phase"
    RELOAD = "reload"
    HANDOVER = "handover"


class SafeExecutor(Protocol):
    async def execute(self, action: Action, before: Snapshot) -> Snapshot: ...
    async def cleanup(self) -> bool | None:
        """Release injected controls and return known pause status (None if unknown)."""
        ...


class CheckpointController(Protocol):
    @property
    def current_snapshot(self) -> Snapshot | None: ...
    async def verify_initial_checkpoint(self, snapshot: Snapshot, state_path: Path
                                        ) -> CheckpointReceipt: ...
    async def save_checkpoint(self, snapshot: Snapshot) -> CheckpointReceipt: ...
    async def load_checkpoint(self, receipt: CheckpointReceipt) -> Snapshot: ...
    def can_end_turn(self, snapshot: Snapshot, receipt: CheckpointReceipt | None) -> bool: ...


class _Stop(Exception):
    def __init__(self, reason: str, affected: tuple[str, ...] = ()) -> None:
        self.reason, self.affected = reason, affected


class BattleSupervisor:
    """One bounded session. Injected adapters are trusted, separately verified gates."""

    def __init__(self, observer: Observer, executor: SafeExecutor,
                 checkpoints: CheckpointController, policy: Policy, initial_state_path: Path, *,
                 incoming_attack: Callable[[Snapshot, CheckpointReceipt], IncomingAttack | None]
                 | None = None, stop_requested: Callable[[], bool] = lambda: False,
                 timeout_seconds: float = 5, max_actions: int = 1000,
                 max_observations: int = 2000) -> None:
        if (not math.isfinite(timeout_seconds) or timeout_seconds <= 0
                or type(max_actions) is not int or max_actions <= 0
                or type(max_observations) is not int or max_observations <= 0):
            raise ValueError("invalid supervisor budgets")
        self._observer, self._executor, self._checkpoints = observer, executor, checkpoints
        self._policy, self._initial_path = policy, initial_state_path
        self._incoming, self._stop = incoming_attack, stop_requested
        self._timeout, self._max_actions, self._max_observations = (
            timeout_seconds, max_actions, max_observations)
        self.state = SupervisorState.STARTUP
        self._used = False
        self._identity: tuple[str | None, ...] | None = None
        self._checkpoint: CheckpointReceipt | None = None
        self._snapshot: Snapshot | None = None
        self._history: list[Action] = []
        self._attempt_reactions: list[FailedReaction] = []
        self._failed_reactions: list[FailedReaction] = []
        self._retries = 0
        self._enemy_turn: int | None = None
        self._restored = False
        self._affected: tuple[str, ...] = ()
        self._known_allies: set[str] = set()
        self._active_allies: set[str] = set()

    def _check_stop(self) -> None:
        if self._stop():
            raise _Stop("user_stop")

    async def _call(self, operation: Callable[[], Awaitable[T]]) -> T:
        self._check_stop()
        deadline = asyncio.get_running_loop().time() + self._timeout
        async with asyncio.timeout_at(deadline):
            result = await operation()
        if asyncio.get_running_loop().time() >= deadline:
            raise TimeoutError("supervisor deadline expired")
        self._check_stop()
        return result

    def _validate(self, snapshot: Snapshot, previous: Snapshot | None = None) -> None:
        identity = (snapshot.game_id, snapshot.patch_id, snapshot.map_id, snapshot.profile_id)
        if (snapshot.validation is not ValidationStatus.VALIDATED
                or snapshot.units is None or snapshot.legal_actions is None
                or snapshot.map_complete is None or type(snapshot.turn) is not int
                or snapshot.turn < 0 or snapshot.phase is Phase.UNKNOWN
                or (self._identity is not None and identity != self._identity)
                or len({unit.id for unit in snapshot.units}) != len(snapshot.units)
                or any(u.affiliation is Affiliation.UNKNOWN or u.defeated is None
                       or u.scripted_departure is None for u in snapshot.units)):
            raise _Stop("invalid_observation")
        if (previous is not None and (snapshot.sequence <= previous.sequence
                                     or snapshot.capture_id == previous.capture_id)):
            raise _Stop("stale_observation")
        if snapshot.screen is Screen.CHOICE:
            raise _Stop("unexpected_choice")
        if snapshot.screen is Screen.UNKNOWN:
            raise _Stop("unknown_screen")
        allies = {u.id: u for u in snapshot.units if u.affiliation is Affiliation.ALLY}
        if snapshot.map_complete is not True and any(
            u.hp is None or u.max_hp is None for u in allies.values()
            if u.scripted_departure is False
        ):
            raise _Stop("invalid_observation")
        if (snapshot.map_complete is not True and self._active_allies - allies.keys()
                - set(snapshot.scripted_departure_ids) - set(snapshot.confirmed_defeated_ids)):
            raise _Stop("unresolved_roster")
        self._known_allies.update(allies)
        self._active_allies = {u.id for u in allies.values()
                              if not u.defeated and not u.scripted_departure}
        self._identity = identity

    def _defeated(self, snapshot: Snapshot) -> tuple[str, ...]:
        assert snapshot.units is not None
        allies = {u.id: u for u in snapshot.units if u.affiliation is Affiliation.ALLY}
        if any(unit_id not in self._known_allies for unit_id in snapshot.confirmed_defeated_ids):
            raise _Stop("invalid_defeat_evidence")
        return tuple(sorted(set(snapshot.confirmed_defeated_ids) | {
            u.id for u in allies.values() if u.defeated is True
            or (u.hp == 0 and u.scripted_departure is False)
        }))

    def _legal(self, action: Action, snapshot: Snapshot) -> None:
        if (action.snapshot_sequence != snapshot.sequence
                or snapshot.legal_actions is None or action not in snapshot.legal_actions):
            raise _Stop("invalid_action")

    async def _execute(self, action: Action, before: Snapshot) -> Snapshot:
        self._legal(action, before)
        if len(self._history) >= self._max_actions:
            raise _Stop("action_budget")
        self._history.append(action)  # Preserve attempted inputs when completion is unknown.
        after = await self._call(lambda: self._executor.execute(action, before))
        self._snapshot = after
        self._validate(after, before)
        if (checkpoint_state_fingerprint(after) == checkpoint_state_fingerprint(before)
                and not self._next_attack(before, after, action)):
            raise _Stop("no_progress")
        return after

    def _next_attack(self, before: Snapshot, after: Snapshot, action: Action) -> bool:
        if (action.kind not in (ActionKind.DEFEND, ActionKind.EVADE, ActionKind.COUNTER)
                or after.screen is not Screen.REACTION or self._incoming is None
                or self._checkpoint is None):
            return False
        previous = self._incoming(before, self._checkpoint)
        current = self._incoming(after, self._checkpoint)
        if (previous is None or current is None or current.key == previous.key
                or current.checkpoint_id != self._checkpoint.checkpoint_id
                or choose_reaction(after, self._policy, 0, (), incoming=current).kind
                is ActionKind.HANDOVER):
            return False
        if (previous.key.checkpoint_id, previous.key.map_id, previous.key.turn,
            previous.key.ally_id, previous.key.attacker_id, previous.key.weapon_id) == (
            current.key.checkpoint_id, current.key.map_id, current.key.turn,
            current.key.ally_id, current.key.attacker_id, current.key.weapon_id):
            return current.occurrence > previous.occurrence
        return True

    def _receipt_valid(self, receipt: CheckpointReceipt, snapshot: Snapshot) -> None:
        if (receipt.verified is not True or not receipt.checkpoint_id
                or (receipt.game_id, receipt.map_id) != (snapshot.game_id, snapshot.map_id)
                or (self._checkpoint is not None and receipt.slot != self._checkpoint.slot)):
            raise _Stop("invalid_checkpoint_receipt")

    async def _end_turn(self, snapshot: Snapshot) -> Snapshot:
        if not self._restored:
            self.state = SupervisorState.CHECKPOINT_SAVE
            receipt = await self._call(lambda: self._checkpoints.save_checkpoint(snapshot))
            self._receipt_valid(receipt, snapshot)
            self._checkpoint = receipt
            current = self._checkpoints.current_snapshot
            if current is None:
                raise _Stop("checkpoint_save_failed")
            self._validate(current, snapshot)
            self._snapshot = snapshot = current
        if not self._checkpoints.can_end_turn(snapshot, self._checkpoint):
            raise _Stop("checkpoint_save_failed")
        actions = [a for a in snapshot.legal_actions or () if a.kind is ActionKind.END_TURN]
        if len(actions) != 1:
            raise _Stop("invalid_end_turn")
        self._enemy_turn = snapshot.turn
        self._restored = False
        self.state = SupervisorState.ENEMY_PHASE
        return await self._execute(actions[0], snapshot)

    async def _reload(self, snapshot: Snapshot, defeated: tuple[str, ...]) -> Snapshot:
        self._affected = defeated
        if self._retries >= self._policy.max_retries:
            raise _Stop("retry_limit", defeated)
        if self._checkpoint is None or self._enemy_turn is None:
            raise _Stop("allied_defeat", defeated)
        self.state = SupervisorState.RELOAD
        receipt = self._checkpoint
        restored = await self._call(lambda: self._checkpoints.load_checkpoint(receipt))
        self._validate(restored, snapshot)
        if (self._defeated(restored) or restored.phase is not Phase.PLAYER
                or restored.turn != self._enemy_turn):
            raise _Stop("checkpoint_load_failed", defeated)
        self._failed_reactions.extend(self._attempt_reactions)
        self._attempt_reactions.clear()
        self._retries += 1  # Only a proven successful reload consumes a retry.
        self._affected = ()
        self._restored = True
        return restored

    async def run(self) -> Handover:
        if self._used:
            raise ValueError("supervisor is single-use")
        self._used = True
        reason = "observation_budget"
        affected: tuple[str, ...] = ()
        paused: bool | None = None
        try:
            snapshot = await self._call(self._observer.observe)
            self._snapshot = snapshot
            self._validate(snapshot)
            if snapshot.map_complete is True:
                raise _Stop("map_complete")
            if snapshot.phase is not Phase.PLAYER or snapshot.screen is not Screen.MAP:
                raise _Stop("initial_checkpoint_failed")
            receipt = await self._call(lambda: self._checkpoints.verify_initial_checkpoint(
                snapshot, self._initial_path))
            self._receipt_valid(receipt, snapshot)
            self._checkpoint = receipt
            initial = self._checkpoints.current_snapshot
            if initial is None:
                raise _Stop("initial_checkpoint_failed")
            self._validate(initial, snapshot)
            snapshot = initial
            for _ in range(self._max_observations):
                self._check_stop()
                self._snapshot = snapshot
                if snapshot.map_complete is True:
                    raise _Stop("map_complete")
                defeated = self._defeated(snapshot)
                if defeated:
                    snapshot = await self._reload(snapshot, defeated)
                    continue
                if snapshot.phase is Phase.PLAYER and snapshot.screen is Screen.MAP:
                    if self._enemy_turn is not None and not self._restored:
                        if snapshot.turn is None or snapshot.turn <= self._enemy_turn:
                            raise _Stop("unexpected_phase")
                        self._retries = 0
                        self._failed_reactions.clear()
                        self._attempt_reactions.clear()
                        self._enemy_turn = None
                    self.state = SupervisorState.PLAYER_PHASE
                    action = choose_action(snapshot, self._policy)
                    if action.kind is ActionKind.HANDOVER:
                        raise _Stop(action.reason or "planner_handover")
                    if self._restored and action.kind is not ActionKind.END_TURN:
                        raise _Stop("checkpoint_load_failed")
                    if action.kind is ActionKind.END_TURN:
                        snapshot = await self._end_turn(snapshot)
                    else:
                        snapshot = await self._execute(action, snapshot)
                elif snapshot.phase is Phase.ENEMY and snapshot.screen is Screen.REACTION:
                    self.state = SupervisorState.ENEMY_PHASE
                    if self._incoming is None or self._checkpoint is None:
                        raise _Stop("unknown_reaction_evidence")
                    incoming = self._incoming(snapshot, self._checkpoint)
                    if incoming is None or incoming.checkpoint_id != self._checkpoint.checkpoint_id:
                        raise _Stop("unknown_reaction_evidence")
                    action = choose_reaction(snapshot, self._policy, self._retries,
                                             self._failed_reactions, incoming=incoming)
                    if action.kind is ActionKind.HANDOVER:
                        raise _Stop(action.reason or "reaction_handover")
                    self._attempt_reactions.append(FailedReaction(incoming.key, action.kind,
                                                                  action.weapon_id))
                    snapshot = await self._execute(action, snapshot)
                elif snapshot.screen is Screen.DIALOGUE:
                    actions = [a for a in snapshot.legal_actions or ()
                               if a.kind is ActionKind.SKIP_DIALOGUE]
                    if (len(actions) != 1 or not isinstance(snapshot.dialogue_id, str)
                            or not snapshot.dialogue_id.strip()):
                        raise _Stop("unrecognized_dialogue")
                    snapshot = await self._execute(actions[0], snapshot)
                elif snapshot.phase in (Phase.ENEMY, Phase.TRANSITION) and snapshot.screen \
                        is Screen.MAP:
                    observed = await self._call(self._observer.observe)
                    self._snapshot = observed
                    self._validate(observed, snapshot)
                    snapshot = observed
                else:
                    raise _Stop("unexpected_transition")
        except _Stop as stop:
            reason, affected = stop.reason, stop.affected
        except asyncio.CancelledError:
            reason = "user_stop"
        except ExecutionError as exc:
            reason = exc.reason
        except ConnectionError:
            reason = "connection_lost"
        except Exception:
            reason = {SupervisorState.STARTUP: "initial_checkpoint_failed",
                      SupervisorState.CHECKPOINT_SAVE: "checkpoint_save_failed",
                      SupervisorState.RELOAD: "checkpoint_load_failed"}.get(
                          self.state, "operation_failed")
        finally:
            try:
                async with asyncio.timeout(self._timeout):
                    paused = await self._executor.cleanup()
            except (Exception, asyncio.CancelledError):
                paused = None
                reason = "cleanup_failed"
            self.state = SupervisorState.HANDOVER
        return Handover(reason, self._checkpoint, self._retries, affected or self._affected,
                        tuple(self._history), paused)
