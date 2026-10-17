"""Synthetic transition recipes; none are validated PPSSPP menu sequences."""

import asyncio
from dataclasses import replace

import pytest

from psp_buddy import executor
from psp_buddy.models import (
    Action,
    ActionKind,
    Affiliation,
    Phase,
    Screen,
    Snapshot,
    Unit,
    ValidationStatus,
)


def state(sequence, kind=ActionKind.WAIT, *, screen=Screen.MAP, phase=Phase.PLAYER, finished=False):
    action = Action(
        kind,
        sequence,
        actor_id="ally",
        target_id=(
            "enemy"
            if kind in (ActionKind.ATTACK, ActionKind.COUNTER)
            else "patient"
            if kind in (ActionKind.REPAIR, ActionKind.TRUST)
            else None
        ),
        weapon_id="weapon" if kind in (ActionKind.ATTACK, ActionKind.COUNTER) else None,
        destination=(2, 2) if kind is ActionKind.MOVE else None,
    )
    unit = Unit(
        "ally",
        "robot",
        Affiliation.ALLY,
        position=(2, 2) if finished else (1, 1),
        hp=100,
        max_hp=100,
        en=50,
        max_en=50,
        sp=10,
        action_available=not finished,
        defeated=False,
        scripted_departure=False,
    )
    return Snapshot(
        sequence,
        "map",
        "game",
        "patch",
        f"capture-{sequence}",
        "profile",
        ValidationStatus.VALIDATED,
        turn=1,
        phase=phase,
        screen=screen,
        units=(
            unit,
            Unit(
                "enemy",
                "enemy",
                Affiliation.ENEMY,
                hp=100,
                max_hp=100,
                defeated=False,
                scripted_departure=False,
            ),
            Unit(
                "patient",
                "robot",
                Affiliation.ALLY,
                hp=50,
                max_hp=100,
                defeated=False,
                scripted_departure=False,
            ),
        ),
        legal_actions=() if finished else (action,),
        map_complete=False,
        dialogue_id="dialogue" if screen is Screen.DIALOGUE else None,
    )


def observed(
    snapshot, kind, *, menu="map", validated=True, decision_free=None, attack_context=None
):
    return executor.ExecutionObservation(
        snapshot,
        menu,
        executor.ActionSelection.from_action(
            Action(
                kind,
                snapshot.sequence,
                "ally",
                (
                    "enemy"
                    if kind in (ActionKind.ATTACK, ActionKind.COUNTER)
                    else "patient"
                    if kind in (ActionKind.REPAIR, ActionKind.TRUST)
                    else None
                ),
                "weapon" if kind in (ActionKind.ATTACK, ActionKind.COUNTER) else None,
                (2, 2) if kind is ActionKind.MOVE else None,
            )
        ),
        "observation-evidence",
        validated,
        decision_free,
        attack_context,
    )


class Adapter:
    def __init__(self, observations):
        self.observations = iter(observations)
        self.sent = []
        self.released = 0
        self.fail_send = False
        self.fail_release = False
        self.block = None

    async def observe(self):
        return next(self.observations)

    async def send(self, command):
        self.sent.append(command)
        if self.fail_send:
            raise ConnectionError("connection lost")
        if self.block is not None:
            self.block.set()
            await asyncio.sleep(5)

    async def release_all(self):
        self.released += 1
        if self.fail_release:
            raise ConnectionError("release failed")
        return None


def setup(
    kind=ActionKind.WAIT,
    *,
    final_screen=Screen.MAP,
    final_phase=Phase.PLAYER,
    starting_screen=Screen.MAP,
    starting_phase=Phase.PLAYER,
):
    assert hasattr(executor, "BoundedExecutor")
    before = state(1, kind, screen=starting_screen, phase=starting_phase)
    fresh = state(2, kind, screen=starting_screen, phase=starting_phase)
    after = state(3, kind, screen=final_screen, phase=final_phase, finished=True)
    decision_free = True if kind is ActionKind.SKIP_DIALOGUE else None
    attack_context = "attack-1" if starting_screen is Screen.REACTION else None
    current = observed(fresh, kind, decision_free=decision_free, attack_context=attack_context)
    result = observed(after, kind, menu="result")
    adapter = Adapter([current, result])
    step = executor.RecipeStep(
        "synthetic-confirm",
        executor.ExpectedContext.from_observation(current),
        executor.ExpectedContext.from_observation(result),
        "step-evidence",
        lambda previous, next_observation, action: (
            next_observation.snapshot.units[0].position == (2, 2)
        ),
    )
    recipe = executor.ActionRecipe(
        before.legal_actions[0],
        executor.RecipeBinding.from_snapshot(before),
        (step,),
        "recipe-evidence",
        True,
        lambda previous, next_snapshot, action: next_snapshot.units[0].action_available is False,
    )
    manager = executor.BoundedExecutor(
        adapter, lambda action, snapshot: recipe, timeout_seconds=0.5, cleanup_timeout_seconds=0.5
    )
    return manager, adapter, before, recipe, current, result


def test_explicit_recipe_executes_one_verified_transition_and_releases():
    manager, adapter, before, _, _, result = setup()
    assert asyncio.run(manager.execute(before.legal_actions[0], before)) == result.snapshot
    assert adapter.sent == ["synthetic-confirm"]
    assert adapter.released == 1


@pytest.mark.parametrize(
    "kind",
    [
        ActionKind.MOVE,
        ActionKind.ATTACK,
        ActionKind.WAIT,
        ActionKind.END_TURN,
        ActionKind.DEFEND,
        ActionKind.EVADE,
        ActionKind.COUNTER,
        ActionKind.SKIP_DIALOGUE,
    ],
)
def test_action_kinds_require_explicit_validated_recipes(kind):
    reaction = kind in (ActionKind.DEFEND, ActionKind.EVADE, ActionKind.COUNTER)
    kwargs = dict(starting_screen=Screen.REACTION, starting_phase=Phase.ENEMY) if reaction else {}
    if kind is ActionKind.SKIP_DIALOGUE:
        kwargs = dict(starting_screen=Screen.DIALOGUE)
    manager, adapter, before, _, _, result = setup(kind, **kwargs)
    assert asyncio.run(manager.execute(before.legal_actions[0], before)) == result.snapshot
    assert adapter.released == 1


@pytest.mark.parametrize("screen", [Screen.CHOICE, Screen.MAP_CLEAR, Screen.UNKNOWN])
def test_choice_mapclear_unknown_never_receive_input(screen):
    manager, adapter, before, _, _, _ = setup()
    before = replace(before, screen=screen)
    with pytest.raises(executor.ExecutionError):
        asyncio.run(manager.execute(before.legal_actions[0], before))
    assert not adapter.sent
    assert adapter.released == 1


def test_missing_recipe_fails_closed_without_input():
    manager, adapter, before, _, _, _ = setup()
    manager = executor.BoundedExecutor(adapter, lambda action, snapshot: None)
    with pytest.raises(executor.ExecutionError):
        asyncio.run(manager.execute(before.legal_actions[0], before))
    assert not adapter.sent
    assert adapter.released == 1


@pytest.mark.parametrize(
    "change",
    [
        dict(map_id="wrong"),
        dict(capture_id="capture-1"),
        dict(
            sequence=1, capture_id="capture-1", legal_actions=(Action(ActionKind.WAIT, 1, "ally"),)
        ),
        dict(validation=ValidationStatus.PARTIAL),
        dict(legal_actions=()),
        dict(units=(replace(state(2).units[0], hp=50),)),
    ],
)
def test_current_observation_must_revalidate_fresh_unchanged_legal_state(change):
    manager, adapter, before, _, current, result = setup()
    adapter.observations = iter(
        [replace(current, snapshot=replace(current.snapshot, **change)), result]
    )
    with pytest.raises(executor.ExecutionError):
        asyncio.run(manager.execute(before.legal_actions[0], before))
    assert not adapter.sent
    assert adapter.released == 1


@pytest.mark.parametrize(
    "change",
    [dict(menu_id="wrong"), dict(validated=False), dict(selection=None), dict(evidence_id="")],
)
def test_menu_identity_and_selection_need_validated_evidence(change):
    manager, adapter, before, _, current, result = setup()
    adapter.observations = iter([replace(current, **change), result])
    with pytest.raises(executor.ExecutionError):
        asyncio.run(manager.execute(before.legal_actions[0], before))
    assert not adapter.sent


def test_final_postcondition_failure_releases_and_disables_reuse():
    manager, adapter, before, recipe, current, result = setup()
    recipe = replace(recipe, postcondition=lambda a, b, c: False)
    manager = executor.BoundedExecutor(adapter, lambda a, b: recipe)
    with pytest.raises(executor.ExecutionError):
        asyncio.run(manager.execute(before.legal_actions[0], before))
    assert adapter.released == 1
    adapter.observations = iter([current, result])
    with pytest.raises(executor.ExecutionError):
        asyncio.run(manager.execute(before.legal_actions[0], before))
    assert len(adapter.sent) == 1


def test_fresh_capture_without_semantic_progress_fails():
    manager, adapter, before, recipe, current, _ = setup()
    same = replace(
        current,
        snapshot=replace(
            current.snapshot,
            sequence=3,
            capture_id="capture-3",
            legal_actions=(Action(ActionKind.WAIT, 3, "ally"),),
        ),
    )
    step = replace(
        recipe.steps[0],
        expected_after=executor.ExpectedContext.from_observation(same),
        postcondition=lambda a, b, c: True,
    )
    recipe = replace(recipe, steps=(step,), postcondition=lambda a, b, c: True)
    adapter.observations = iter([current, same])
    manager = executor.BoundedExecutor(adapter, lambda a, b: recipe)
    with pytest.raises(executor.ExecutionError, match="no_progress"):
        asyncio.run(manager.execute(before.legal_actions[0], before))
    assert adapter.released == 1


def test_user_stop_releases_without_input():
    _, adapter, before, recipe, _, _ = setup()
    manager = executor.BoundedExecutor(adapter, lambda a, b: recipe, stop_requested=lambda: True)
    with pytest.raises(executor.ExecutionError, match="user_stop"):
        asyncio.run(manager.execute(before.legal_actions[0], before))
    assert not adapter.sent and adapter.released == 1


def test_send_connection_failure_releases():
    manager, adapter, before, _, _, _ = setup()
    adapter.fail_send = True
    with pytest.raises(executor.ExecutionError):
        asyncio.run(manager.execute(before.legal_actions[0], before))
    assert adapter.released == 1


def test_deadline_releases_and_stops():
    manager, adapter, before, _, _, _ = setup()
    adapter.block = asyncio.Event()
    with pytest.raises(executor.ExecutionError, match="timeout"):
        asyncio.run(manager.execute(before.legal_actions[0], before))
    assert adapter.released == 1


def test_cancellation_waits_for_release():
    manager, adapter, before, _, _, _ = setup()

    async def run():
        adapter.block = asyncio.Event()
        task = asyncio.create_task(manager.execute(before.legal_actions[0], before))
        await adapter.block.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert adapter.released == 1

    asyncio.run(run())


def test_cleanup_failure_is_reported():
    manager, adapter, before, _, _, _ = setup()
    adapter.fail_release = True
    with pytest.raises(executor.ExecutionError, match="cleanup_failed"):
        asyncio.run(manager.execute(before.legal_actions[0], before))


def test_two_step_graph_stops_before_second_input_on_unknown_choice():
    manager, adapter, before, recipe, current, result = setup()
    middle = replace(result, snapshot=replace(result.snapshot, screen=Screen.MENU), menu_id="menu")
    end = replace(result, snapshot=replace(result.snapshot, sequence=4, capture_id="capture-4"))
    first = replace(
        recipe.steps[0], expected_after=executor.ExpectedContext.from_observation(middle)
    )
    second = executor.RecipeStep(
        "synthetic-final",
        first.expected_after,
        executor.ExpectedContext.from_observation(end),
        "second-evidence",
        lambda a, b, c: True,
    )
    recipe = replace(recipe, steps=(first, second))
    wrong = replace(middle, snapshot=replace(middle.snapshot, screen=Screen.CHOICE))
    adapter.observations = iter([current, wrong, end])
    manager = executor.BoundedExecutor(adapter, lambda a, b: recipe)
    with pytest.raises(executor.ExecutionError, match="unexpected_choice"):
        asyncio.run(manager.execute(before.legal_actions[0], before))
    assert adapter.sent == ["synthetic-confirm"] and adapter.released == 1


@pytest.mark.parametrize(
    "change",
    [
        dict(validated=False),
        dict(evidence_id=""),
        dict(binding=executor.RecipeBinding("wrong", "patch", "map", "profile", 1, "capture-1")),
        dict(steps=()),
    ],
)
def test_unvalidated_or_wrong_binding_recipe_never_inputs(change):
    _, adapter, before, recipe, _, _ = setup()
    recipe = replace(recipe, **change)
    manager = executor.BoundedExecutor(adapter, lambda a, b: recipe)
    with pytest.raises(executor.ExecutionError):
        asyncio.run(manager.execute(before.legal_actions[0], before))
    assert not adapter.sent


def test_recipe_step_budget_is_checked_before_any_input():
    _, adapter, before, recipe, _, _ = setup()
    recipe = replace(recipe, steps=(recipe.steps[0],) * 3)
    manager = executor.BoundedExecutor(adapter, lambda a, b: recipe, max_steps=2)
    with pytest.raises(executor.ExecutionError):
        asyncio.run(manager.execute(before.legal_actions[0], before))
    assert not adapter.sent


@pytest.mark.parametrize("decision_free", [None, False])
def test_dialogue_needs_positive_decision_free_evidence(decision_free):
    manager, adapter, before, _, current, result = setup(
        ActionKind.SKIP_DIALOGUE, starting_screen=Screen.DIALOGUE
    )
    adapter.observations = iter([replace(current, decision_free_dialogue=decision_free), result])
    with pytest.raises(executor.ExecutionError, match="unknown_dialogue"):
        asyncio.run(manager.execute(before.legal_actions[0], before))
    assert not adapter.sent


def test_same_dialogue_with_changed_menu_identity_is_not_advancement():
    _, adapter, before, recipe, current, _ = setup(
        ActionKind.SKIP_DIALOGUE, starting_screen=Screen.DIALOGUE
    )
    after = replace(
        current,
        menu_id="changed-frame",
        snapshot=replace(
            current.snapshot,
            sequence=3,
            capture_id="capture-3",
            legal_actions=(replace(before.legal_actions[0], snapshot_sequence=3),),
        ),
    )
    recipe = replace(
        recipe,
        steps=(
            replace(
                recipe.steps[0],
                expected_after=executor.ExpectedContext.from_observation(after),
                postcondition=lambda a, b, c: True,
            ),
        ),
        postcondition=lambda a, b, c: True,
    )
    adapter.observations = iter([current, after])
    manager = executor.BoundedExecutor(adapter, lambda a, b: recipe)
    with pytest.raises(executor.ExecutionError, match="dialogue_progress"):
        asyncio.run(manager.execute(before.legal_actions[0], before))


def test_successful_executor_rejects_old_originating_snapshot_replay():
    manager, adapter, before, _, current, result = setup()
    asyncio.run(manager.execute(before.legal_actions[0], before))
    adapter.observations = iter([current, result])
    with pytest.raises(executor.ExecutionError, match="stale"):
        asyncio.run(manager.execute(before.legal_actions[0], before))
    assert len(adapter.sent) == 1


def test_legal_action_with_missing_roster_target_is_rejected_before_send():
    _, adapter, before, recipe, current, result = setup(ActionKind.ATTACK)
    action = replace(before.legal_actions[0], target_id="missing")
    before = replace(before, legal_actions=(action,))
    selection = executor.ActionSelection.from_action(action)
    current = replace(
        current,
        selection=selection,
        snapshot=replace(current.snapshot, legal_actions=(replace(action, snapshot_sequence=2),)),
    )
    step = replace(
        recipe.steps[0], expected_before=executor.ExpectedContext.from_observation(current)
    )
    recipe = replace(recipe, action=action, steps=(step,))
    adapter.observations = iter([current, result])
    manager = executor.BoundedExecutor(adapter, lambda a, b: recipe)
    with pytest.raises(executor.ExecutionError, match="invalid_action_target"):
        asyncio.run(manager.execute(action, before))
    assert not adapter.sent


def test_unknown_reaction_attack_context_never_sends():
    manager, adapter, before, _, current, result = setup(
        ActionKind.DEFEND, starting_screen=Screen.REACTION, starting_phase=Phase.ENEMY
    )
    adapter.observations = iter([replace(current, attack_context_id=None), result])
    with pytest.raises(executor.ExecutionError):
        asyncio.run(manager.execute(before.legal_actions[0], before))
    assert not adapter.sent


def test_synchronous_recipe_provider_cannot_silently_exceed_deadline():
    import time

    _, adapter, before, recipe, _, _ = setup()

    def slow(a, b):
        time.sleep(0.06)
        return recipe

    manager = executor.BoundedExecutor(adapter, slow, timeout_seconds=0.05)
    with pytest.raises(executor.ExecutionError, match="timeout"):
        asyncio.run(manager.execute(before.legal_actions[0], before))
    assert not adapter.sent and adapter.released == 1


def test_repeated_cancellation_still_waits_for_bounded_release():
    manager, adapter, before, _, _, _ = setup()

    async def run():
        releasing = asyncio.Event()
        finish_release = asyncio.Event()

        async def release():
            adapter.released += 1
            releasing.set()
            await finish_release.wait()
            return None

        adapter.release_all = release
        adapter.block = asyncio.Event()
        task = asyncio.create_task(manager.execute(before.legal_actions[0], before))
        await adapter.block.wait()
        task.cancel()
        await releasing.wait()
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        finish_release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert adapter.released == 1

    asyncio.run(run())


def test_unexplained_allied_disappearance_blocks_even_permissive_postconditions():
    _, adapter, before, recipe, current, result = setup()
    result = replace(result, snapshot=replace(result.snapshot, units=result.snapshot.units[1:]))
    recipe = replace(
        recipe,
        steps=(
            replace(
                recipe.steps[0],
                expected_after=executor.ExpectedContext.from_observation(result),
                postcondition=lambda a, b, c: True,
            ),
        ),
        postcondition=lambda a, b, c: True,
    )
    adapter.observations = iter([current, result])
    manager = executor.BoundedExecutor(adapter, lambda a, b: recipe)
    with pytest.raises(executor.ExecutionError, match="unresolved_roster"):
        asyncio.run(manager.execute(before.legal_actions[0], before))
    assert adapter.released == 1


@pytest.mark.parametrize("mode", ["present", "confirmed_missing", "map_clear"])
def test_verified_final_defeat_or_mapclear_returns_for_supervision(mode):
    _, adapter, before, recipe, current, result = setup(
        ActionKind.DEFEND, starting_screen=Screen.REACTION, starting_phase=Phase.ENEMY
    )
    if mode == "present":
        final = replace(
            result.snapshot,
            units=(replace(result.snapshot.units[0], hp=0, defeated=True),)
            + result.snapshot.units[1:],
        )
    elif mode == "confirmed_missing":
        final = replace(
            result.snapshot, units=result.snapshot.units[1:], confirmed_defeated_ids=("ally",)
        )
    else:
        final = replace(result.snapshot, units=(), screen=Screen.MAP_CLEAR, map_complete=True)
    result = replace(result, snapshot=final)
    recipe = replace(
        recipe,
        steps=(
            replace(
                recipe.steps[0],
                expected_after=executor.ExpectedContext.from_observation(result),
                postcondition=lambda a, b, c: True,
            ),
        ),
        postcondition=lambda a, b, c: True,
    )
    adapter.observations = iter([current, result])
    manager = executor.BoundedExecutor(adapter, lambda a, b: recipe)
    assert asyncio.run(manager.execute(before.legal_actions[0], before)) == final
    assert not manager._disabled
    assert adapter.released == 1


def test_intermediate_defeat_stops_before_further_input():
    _, adapter, before, recipe, current, result = setup()
    fallen = replace(
        result,
        snapshot=replace(
            result.snapshot,
            units=(replace(result.snapshot.units[0], hp=0, defeated=True),)
            + result.snapshot.units[1:],
        ),
    )
    first = replace(
        recipe.steps[0],
        expected_after=executor.ExpectedContext.from_observation(fallen),
        postcondition=lambda a, b, c: True,
    )
    second = executor.RecipeStep(
        "must-not-send",
        first.expected_after,
        recipe.steps[0].expected_after,
        "second",
        lambda a, b, c: True,
    )
    recipe = replace(recipe, steps=(first, second), postcondition=lambda a, b, c: True)
    adapter.observations = iter([current, fallen])
    manager = executor.BoundedExecutor(adapter, lambda a, b: recipe)
    with pytest.raises(executor.ExecutionError, match="allied_defeat"):
        asyncio.run(manager.execute(before.legal_actions[0], before))
    assert adapter.sent == ["synthetic-confirm"]
    assert adapter.released == 1


def test_contradictory_defeat_and_departure_refuses_startup_input():
    _, adapter, before, _, _, _ = setup()
    before = replace(
        before,
        units=(replace(before.units[0], defeated=True, scripted_departure=True),)
        + before.units[1:],
    )
    manager = executor.BoundedExecutor(adapter, lambda a, b: None)
    with pytest.raises(executor.ExecutionError, match="contradictory"):
        asyncio.run(manager.execute(before.legal_actions[0], before))
    assert not adapter.sent


@pytest.mark.parametrize("kind", [ActionKind.REPAIR, ActionKind.TRUST])
def test_excluded_mvp_action_rejects_valid_legal_recipe_before_observation(kind):
    _, adapter, before, recipe, _, _ = setup(kind)
    observations = []
    recipes = []
    original_observe = adapter.observe

    async def observe():
        observations.append("observe")
        return await original_observe()

    def provide(action, snapshot):
        recipes.append(action)
        return recipe

    adapter.observe = observe
    manager = executor.BoundedExecutor(adapter, provide)
    with pytest.raises(executor.ExecutionError, match="^excluded_mvp_action$"):
        asyncio.run(manager.execute(before.legal_actions[0], before))
    assert not observations
    assert not recipes
    assert not adapter.sent
    assert adapter.released == 1
    assert manager._disabled
