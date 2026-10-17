"""Bounded evidence-driven transitions; no production menu sequences are provided.

Recipes and adapter observations are trusted integration seams, not a live gate.
Evidence identifiers refer to separately reviewed menu/input calibration. No input
is inferred from ActionKind, and a recipe cannot be reused for another snapshot.
"""

import asyncio
import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from .checkpoint import checkpoint_state_fingerprint
from .models import (
    Action,
    ActionKind,
    Affiliation,
    Phase,
    Position,
    Screen,
    Snapshot,
    ValidationStatus,
)


class ExecutionError(ValueError):
    """Uncertain execution requires handover; it must never trigger blind retries."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class ActionSelection:
    kind: ActionKind
    actor_id: str | None
    target_id: str | None
    weapon_id: str | None
    destination: Position | None

    @classmethod
    def from_action(cls, action: Action) -> "ActionSelection":
        return cls(
            action.kind, action.actor_id, action.target_id, action.weapon_id, action.destination
        )


@dataclass(frozen=True)
class ExecutionObservation:
    snapshot: Snapshot
    menu_id: str | None
    selection: ActionSelection | None
    evidence_id: str
    validated: bool = False
    decision_free_dialogue: bool | None = None
    attack_context_id: str | None = None


@dataclass(frozen=True)
class ExpectedContext:
    screen: Screen
    phase: Phase
    menu_id: str
    selection: ActionSelection | None
    dialogue_id: str | None = None
    attack_context_id: str | None = None

    @classmethod
    def from_observation(cls, observation: ExecutionObservation) -> "ExpectedContext":
        if not observation.menu_id:
            raise ValueError("expected context requires menu identity")
        return cls(
            observation.snapshot.screen,
            observation.snapshot.phase,
            observation.menu_id,
            observation.selection,
            observation.snapshot.dialogue_id,
            observation.attack_context_id,
        )


@dataclass(frozen=True)
class RecipeBinding:
    game_id: str | None
    patch_id: str | None
    map_id: str | None
    profile_id: str | None
    sequence: int
    capture_id: str | None

    @classmethod
    def from_snapshot(cls, snapshot: Snapshot) -> "RecipeBinding":
        return cls(
            snapshot.game_id,
            snapshot.patch_id,
            snapshot.map_id,
            snapshot.profile_id,
            snapshot.sequence,
            snapshot.capture_id,
        )


StepPostcondition = Callable[[ExecutionObservation, ExecutionObservation, Action], bool]
ActionPostcondition = Callable[[Snapshot, Snapshot, Action], bool]


@dataclass(frozen=True)
class RecipeStep:
    command: str
    expected_before: ExpectedContext
    expected_after: ExpectedContext
    evidence_id: str
    postcondition: StepPostcondition


@dataclass(frozen=True)
class ActionRecipe:
    action: Action
    binding: RecipeBinding
    steps: tuple[RecipeStep, ...]
    evidence_id: str
    validated: bool
    postcondition: ActionPostcondition


class ExecutionAdapter(Protocol):
    """Bounded primitives calibrated independently; observe never issues input.

    send must execute one finite adapter-defined command. release_all releases all
    injected controls, never toggles pause, and returns authoritative pause status
    only when known. No supported live adapter is implemented in this module.
    """

    async def observe(self) -> ExecutionObservation: ...
    async def send(self, command: str) -> None: ...
    async def release_all(self) -> bool | None: ...


RecipeProvider = Callable[[Action, Snapshot], ActionRecipe | None]


def _identity(snapshot: Snapshot) -> tuple[str | None, ...]:
    return snapshot.game_id, snapshot.patch_id, snapshot.map_id, snapshot.profile_id


def _legal(snapshot: Snapshot) -> tuple[ActionSelection, ...]:
    return tuple(ActionSelection.from_action(a) for a in snapshot.legal_actions or ())


def _progress(observation: ExecutionObservation) -> tuple[object, ...]:
    return (
        checkpoint_state_fingerprint(observation.snapshot),
        observation.menu_id,
        observation.selection,
        observation.attack_context_id,
    )


class BoundedExecutor:
    """Serialize one recipe, verify every transition, and release on every exit.

    Postcondition predicates must be separately reviewed pure bounded functions.
    Arbitrary Python predicates cannot be preempted, so deadlines are also checked
    after each synchronous predicate and every adapter operation. Uncertainty
    permanently disables this executor; create a fresh protected session.
    """

    def __init__(
        self,
        adapter: ExecutionAdapter,
        recipes: RecipeProvider,
        *,
        stop_requested: Callable[[], bool] = lambda: False,
        max_steps: int = 16,
        timeout_seconds: float = 5,
        cleanup_timeout_seconds: float = 2,
    ) -> None:
        if (
            type(max_steps) is not int
            or not 1 <= max_steps <= 64
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
            or not math.isfinite(cleanup_timeout_seconds)
            or cleanup_timeout_seconds <= 0
        ):
            raise ValueError("invalid execution budgets")
        self._adapter, self._recipes, self._stop = adapter, recipes, stop_requested
        self._max_steps, self._timeout, self._cleanup_timeout = (
            max_steps,
            timeout_seconds,
            cleanup_timeout_seconds,
        )
        self._disabled = False
        self._lock = asyncio.Lock()
        self._last: Snapshot | None = None

    def _check(self, deadline: float) -> None:
        if self._stop():
            raise ExecutionError("user_stop")
        if asyncio.get_running_loop().time() >= deadline:
            raise ExecutionError("timeout")

    def _snapshot(
        self,
        snapshot: Snapshot,
        identity: tuple[str | None, ...],
        *,
        previous: Snapshot | None = None,
        terminal: bool = False,
    ) -> None:
        if (
            snapshot.validation is not ValidationStatus.VALIDATED
            or _identity(snapshot) != identity
            or not all(identity)
            or snapshot.phase is Phase.UNKNOWN
            or type(snapshot.turn) is not int
            or snapshot.turn < 0
            or snapshot.units is None
            or snapshot.legal_actions is None
            or type(snapshot.map_complete) is not bool
            or len({u.id for u in snapshot.units}) != len(snapshot.units)
            or any(
                u.affiliation is Affiliation.UNKNOWN
                or u.defeated is None
                or u.scripted_departure is None
                for u in snapshot.units
            )
        ):
            raise ExecutionError("invalid_observation")
        if previous is not None and (
            snapshot.sequence <= previous.sequence or snapshot.capture_id == previous.capture_id
        ):
            raise ExecutionError("stale_observation")
        known_allies = {u.id for u in snapshot.units if u.affiliation is Affiliation.ALLY}
        if previous is not None and previous.units is not None:
            known_allies.update(u.id for u in previous.units if u.affiliation is Affiliation.ALLY)
        confirmed = set(snapshot.confirmed_defeated_ids)
        departed = set(snapshot.scripted_departure_ids)
        if confirmed - known_allies:
            raise ExecutionError("invalid_defeat_evidence")
        if confirmed & departed or any(
            u.defeated is True and u.scripted_departure is True for u in snapshot.units
        ):
            raise ExecutionError("contradictory_defeat_departure")
        defeated = bool(confirmed) or any(
            u.affiliation is Affiliation.ALLY
            and u.scripted_departure is False
            and (u.defeated is True or u.hp == 0)
            for u in snapshot.units
        )
        if defeated and not terminal:
            raise ExecutionError("allied_defeat")
        if previous is not None and previous.units is not None:
            active_allies = {
                unit.id
                for unit in previous.units
                if unit.affiliation is Affiliation.ALLY
                and unit.scripted_departure is False
                and unit.defeated is False
            }
            current_ids = {unit.id for unit in snapshot.units}
            resolved_missing = departed | (confirmed if terminal else set())
            if active_allies - current_ids - resolved_missing and not (
                terminal and snapshot.map_complete is True
            ):
                raise ExecutionError("unresolved_roster")
        if snapshot.screen is Screen.CHOICE:
            raise ExecutionError("unexpected_choice")
        if snapshot.screen is Screen.UNKNOWN:
            raise ExecutionError("unknown_screen")
        if snapshot.screen is Screen.MAP_CLEAR or snapshot.map_complete is True:
            if not terminal:
                raise ExecutionError("map_complete")
        if any(
            u.affiliation is Affiliation.ALLY
            and u.scripted_departure is False
            and (u.hp is None or u.max_hp is None)
            for u in snapshot.units
        ):
            raise ExecutionError("unknown_ally_safety")

    def _context(
        self,
        observation: ExecutionObservation,
        expected: ExpectedContext,
        action: Action,
        *,
        sending: bool,
    ) -> None:
        if (
            observation.validated is not True
            or not observation.evidence_id.strip()
            or not observation.menu_id
            or ExpectedContext.from_observation(observation) != expected
        ):
            raise ExecutionError("unexpected_menu_context")
        if (
            observation.selection is not None
            and observation.selection != ActionSelection.from_action(action)
        ):
            raise ExecutionError("unexpected_action_selection")
        if sending and observation.selection is None:
            raise ExecutionError("unknown_action_selection")
        if observation.snapshot.screen is Screen.DIALOGUE:
            if (
                observation.decision_free_dialogue is not True
                or not observation.snapshot.dialogue_id
                or action.kind is not ActionKind.SKIP_DIALOGUE
            ):
                raise ExecutionError("unknown_dialogue")
        if observation.snapshot.screen is Screen.REACTION and not observation.attack_context_id:
            raise ExecutionError("unknown_attack_context")

    def _recipe(self, action: Action, before: Snapshot) -> ActionRecipe:
        recipe = self._recipes(action, before)
        if (
            recipe is None
            or recipe.validated is not True
            or not recipe.evidence_id.strip()
            or recipe.action != action
            or recipe.binding != RecipeBinding.from_snapshot(before)
            or type(recipe.steps) is not tuple
            or not 1 <= len(recipe.steps) <= self._max_steps
            or not callable(recipe.postcondition)
        ):
            raise ExecutionError("unsupported_action_recipe")
        for step in recipe.steps:
            if (
                not step.command
                or len(step.command) > 128
                or not step.evidence_id.strip()
                or not callable(step.postcondition)
            ):
                raise ExecutionError("invalid_recipe_step")
        if any(
            recipe.steps[i].expected_after != recipe.steps[i + 1].expected_before
            for i in range(len(recipe.steps) - 1)
        ):
            raise ExecutionError("inconsistent_recipe_graph")
        return recipe

    def _action_roster(self, action: Action, snapshot: Snapshot) -> None:
        assert snapshot.units is not None
        roster = {unit.id: unit for unit in snapshot.units}
        actor_kinds = {
            ActionKind.MOVE,
            ActionKind.ATTACK,
            ActionKind.REPAIR,
            ActionKind.TRUST,
            ActionKind.WAIT,
            ActionKind.DEFEND,
            ActionKind.EVADE,
            ActionKind.COUNTER,
        }
        if action.kind in actor_kinds:
            actor = roster.get(action.actor_id or "")
            if actor is None or actor.affiliation is not Affiliation.ALLY:
                raise ExecutionError("invalid_action_actor")
            if actor.scripted_departure is not False or actor.defeated is not False:
                raise ExecutionError("invalid_action_actor")
        target_kinds = {ActionKind.ATTACK, ActionKind.COUNTER, ActionKind.REPAIR, ActionKind.TRUST}
        if action.kind in target_kinds:
            target = roster.get(action.target_id or "")
            affiliation = (
                Affiliation.ENEMY
                if action.kind in (ActionKind.ATTACK, ActionKind.COUNTER)
                else Affiliation.ALLY
            )
            if (
                target is None
                or target.affiliation is not affiliation
                or target.defeated is not False
                or target.scripted_departure is not False
            ):
                raise ExecutionError("invalid_action_target")
        if action.kind is ActionKind.MOVE and (
            action.destination is None
            or len(action.destination) != 2
            or any(type(n) is not int or n < 0 for n in action.destination)
        ):
            raise ExecutionError("invalid_action_destination")
        if action.kind in (ActionKind.ATTACK, ActionKind.COUNTER) and not action.weapon_id:
            raise ExecutionError("invalid_action_weapon")

    async def cleanup(self) -> bool | None:
        deadline = asyncio.get_running_loop().time() + self._cleanup_timeout
        try:
            async with asyncio.timeout_at(deadline):
                paused = await self._adapter.release_all()
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError("cleanup deadline expired")
            if paused is not None and type(paused) is not bool:
                raise ValueError("unknown cleanup pause status")
            return paused
        except Exception as exc:
            self._disabled = True
            raise ExecutionError("cleanup_failed") from exc

    async def _shielded_cleanup(self) -> None:
        task = asyncio.create_task(self.cleanup())
        cancelled = False
        while True:
            try:
                await asyncio.shield(task)
                break
            except asyncio.CancelledError:
                # Repeated stop requests cannot abandon the bounded release task.
                self._disabled = True
                cancelled = True
                if task.done():
                    task.result()
                    break
        if cancelled:
            raise asyncio.CancelledError

    async def execute(self, action: Action, before: Snapshot) -> Snapshot:
        async with self._lock:
            try:
                if self._disabled:
                    raise ExecutionError("executor_disabled")
                if action.kind in (ActionKind.REPAIR, ActionKind.TRUST):
                    raise ExecutionError("excluded_mvp_action")
                deadline = asyncio.get_running_loop().time() + self._timeout
                async with asyncio.timeout_at(deadline):
                    self._check(deadline)
                    self._snapshot(before, _identity(before))
                    if self._last is not None and (
                        before.sequence < self._last.sequence
                        or (before.sequence == self._last.sequence and before != self._last)
                        or _identity(before) != _identity(self._last)
                    ):
                        raise ExecutionError("stale_originating_snapshot")
                    if (
                        action.kind is ActionKind.HANDOVER
                        or action.snapshot_sequence != before.sequence
                        or action not in (before.legal_actions or ())
                    ):
                        raise ExecutionError("invalid_action")
                    self._action_roster(action, before)
                    recipe = self._recipe(action, before)
                    self._check(deadline)
                    current = await self._adapter.observe()
                    self._check(deadline)
                    self._snapshot(current.snapshot, _identity(before), previous=before)
                    if (
                        checkpoint_state_fingerprint(current.snapshot)
                        != checkpoint_state_fingerprint(before)
                        or _legal(current.snapshot) != _legal(before)
                        or ActionSelection.from_action(action) not in _legal(current.snapshot)
                    ):
                        raise ExecutionError("changed_action_evidence")
                    for index, step in enumerate(recipe.steps):
                        self._context(current, step.expected_before, action, sending=True)
                        self._check(deadline)
                        await self._adapter.send(step.command)
                        self._check(deadline)
                        after = await self._adapter.observe()
                        self._check(deadline)
                        self._snapshot(
                            after.snapshot,
                            _identity(before),
                            previous=current.snapshot,
                            terminal=index == len(recipe.steps) - 1,
                        )
                        self._context(after, step.expected_after, action, sending=False)
                        if _progress(after) == _progress(current):
                            raise ExecutionError("no_progress")
                        if step.postcondition(current, after, action) is not True:
                            raise ExecutionError("step_postcondition_failed")
                        self._check(deadline)
                        current = after
                    if (
                        action.kind is ActionKind.SKIP_DIALOGUE
                        and current.snapshot.screen is Screen.DIALOGUE
                        and current.snapshot.dialogue_id == before.dialogue_id
                    ):
                        raise ExecutionError("no_dialogue_progress")
                    if recipe.postcondition(before, current.snapshot, action) is not True:
                        raise ExecutionError("action_postcondition_failed")
                    self._check(deadline)
                    self._last = current.snapshot
                    return current.snapshot
            except asyncio.CancelledError:
                self._disabled = True
                raise
            except ExecutionError:
                self._disabled = True
                raise
            except TimeoutError as exc:
                self._disabled = True
                raise ExecutionError("timeout") from exc
            except Exception as exc:
                self._disabled = True
                raise ExecutionError("adapter_or_recipe_failed") from exc
            finally:
                await self._shielded_cleanup()
