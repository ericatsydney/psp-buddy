"""`plan_and_act`: choose one attack from a policy, run it to the forecast, fire only if it agrees.

Order: read state and weapons, `tactics.plan_attack`; when nothing is in reach from the current
tile, open the unit's Move range once (select, Move, read, back out) and plan again with moves;
`act.run_act(commit=False)` to the forecast; gate; then `phase="fire"` or back out with Cross.
The gate compares what the game shows with what was planned: the same weapon and target, the hit
chance seen when the target was chosen equals the forecast (and the planned one when known), and
the chance is at least `min_hit`. Every fired attack appends the observed deltas to a damage log
so the damage model of docs/research/2026-10-21-damage-model.md can be fitted later. With the
policy clause `use sense then focus before attacking`, a unit whose plan has an attack first casts
Sense or Focus (`spirit_cast`, once, from the map); the result then carries `spirit`, and the
planned hit no longer gates the forecast because the spirit changes it.

M16 ally safety (3 Nov): with the turn-1 hold or advance clauses the pilot's spirits are read once
(an unreadable list counts as no Focus/Sense) and the turn comes from the state. A held unit gets
no input; an advance (a plan with `move_to` and no attack) moves, then Standby, phase `advanced`.
"""

import json
from collections.abc import Collection, Mapping
from pathlib import Path
from typing import Any, cast

from . import act, press_budget, spirit_cast, targets
from .models import Policy
from .spirits import choose_spirit
from .tactics import (
    BOSS_HP_FACTOR,
    BOSS_NAMES,
    SAFE_SPIRITS,
    boss_objects,
    foe_reach_of,
    plan_attack,
    spirited,
)

MIN_HIT = 1
MAX_REPLANS = 2          # extra plans after the game refuses a weapon (greyed, out of reach)
REPLAN_STAGES = ("weapon", "target", "forecast")
BACK_OUT_PAUSE = 0.6
STANDBY_POLLS = 4
STANDBY_NEEDS = 10.0     # seconds two presses and the confirming reads take


OVERLAY_NEEDS = act.FIRE_NEEDS + 20.0     # seconds left to open the Move range and still fire
REPLAN_NEEDS = act.FIRE_NEEDS + 22.0      # a new plan reaches the forecast in about 22 s


async def _back_out(io: act.ActIO, presses: int) -> bool:
    """Cross out of open menus; False when an input failed (reported, never raised)."""
    try:
        for _ in range(presses):
            await io.press("cross", 2)
            await io.sleep(BACK_OUT_PAUSE)
    except act.ActIOError:
        return False
    return True


async def _standby(io: act.ActIO, unit_object: int) -> bool:
    """MVP rule (user, 22 Oct): a moved unit that cannot finish its attack waits.

    After the back-out the post-move menu is up with Attack highlighted and Standby last (22 Oct
    live: Attack / Standby; 26 Oct stage 33, Methuss: Attack / Repair / Standby). The menu wraps
    (31 Oct recon m14rec3), so one Up reaches Standby whatever the length. With the post-move
    menu read (its own slot; the Command-menu slot keeps the earlier menu) Up is pressed only
    from Attack and Circle only once the cursor is seen on the last entry. Memory confirms the
    unit is done; otherwise Cross closes whatever opened and False is reported (never raised).
    """
    if io.time_left() < STANDBY_NEEDS:
        return False                   # the helper's hard cancel must never hit an open menu
    reader = getattr(io, "post_move_menu", None)
    try:
        on_last = False
        masks = await spirit_cast.menu_masks(io) if reader is not None else None
        if reader is not None and masks is not None:
            # M16: the post-move entry bitmask gives Standby's row (a ship lists it first).
            menu = await reader()
            if menu is None or menu[0] != 0:
                return False
            target = spirit_cast.entry_row(masks[1], menu[1], spirit_cast.STANDBY_BIT)
            if target is None:
                return False
            for _ in range(target):
                await io.press("down", 2)
                await io.sleep(0.3)
            menu = await reader()
            if menu is None or menu[0] != target:
                return False
            on_last = True              # verified on Standby: Circle without the Up path
        elif reader is not None:
            menu = await reader()
            # M16: a move with no foe in reach may offer Standby alone. Only a one-entry menu is
            # trusted: a longer one on its last row may be an earlier unit's stale Standby.
            on_last = menu is not None and menu[1] == 1 and menu[0] == 0
            if menu is None or not on_last and (menu[0] != 0 or menu[1] < 2):
                return False
        if not on_last:
            await io.press("up", 2)
            await io.sleep(0.3)
        if reader is not None and not on_last:
            menu = await reader()
            if menu is None or menu[0] != menu[1] - 1:
                return False
        await io.press("circle", 2)
        for _ in range(STANDBY_POLLS):
            await io.sleep(0.6)
            state: Mapping[str, Any] = await io.state()
            unit = next((u for u in state.get("units", []) if u.get("object") == unit_object),
                        None)
            if unit is not None and unit.get("counted_as_unmoved") is False:
                return True
        await _back_out(io, 1)
    except act.ActIOError:
        pass
    return False


def forecast_gate(instruction: Mapping[str, Any], outcome: Mapping[str, Any],
                  expect: Mapping[str, Any], min_hit: int = MIN_HIT) -> str | None:
    """None when the forecast agrees with the plan, else the reason not to fire."""
    stages = {s.get("stage"): s.get("facts", {}) for s in outcome.get("stages", [])}
    forecast, target, planned = stages.get("forecast"), stages.get("target"), stages.get("plan")
    if not forecast or not target or not planned:
        return "forecast_incomplete"
    attack = instruction["attack"]
    if planned.get("target") != attack["target_object"] or planned.get("weapon") != attack[
            "weapon"]:
        return "plan_mismatch"
    hit = forecast.get("hit")
    if type(hit) is not int or not 0 <= hit <= 100:
        return "forecast_hit_unreadable"
    if target.get("hit") != hit:
        return "hit_changed_between_target_and_forecast"
    if expect.get("hit") is not None and expect["hit"] != hit:
        return "forecast_differs_from_plan"
    if hit < min_hit:
        return "hit_too_low"
    return None


async def _open_move_range(io: act.ActIO, unit_object: int) -> Mapping[str, object]:
    """Select the unit and show its Move range, read the state, close the menus again.

    Whether the range really is this unit's is checked by `tactics` (centred overlay), so a menu
    that did not open yields no move plan instead of a wrong one.
    """
    state: Mapping[str, Any] = await io.state()
    unit = next((u for u in state.get("units", []) if u.get("object") == unit_object), None)
    if unit is None:
        raise act.ActIOError("unit not found")
    walk = await io.goto([unit["tile_x"], unit["tile_y"]])
    if not walk.get("reached"):
        raise act.ActIOError("cursor did not reach the unit")
    try:
        await io.press("circle", 2)
        await io.sleep(0.8)
        await io.press("circle", 2)
        await io.sleep(0.8)
        return await act.range_when_drawn(io, [unit["tile_x"], unit["tile_y"]])
    finally:
        await _back_out(io, 2)


def _damage_record(plan: Mapping[str, Any], gate_hit: int, fired: Mapping[str, Any],
                   state: Mapping[str, Any]) -> dict[str, Any]:
    instruction, expect = plan["act"], plan["expect"]
    target = instruction["attack"]["target_object"]
    units = {u["object"]: u for u in state.get("units", [])}
    victim = units.get(target, {})
    grid = state.get("map", {})
    terrain: Any = None
    rows: Any = grid.get("terrain_rows") if isinstance(grid, Mapping) else None
    try:
        terrain = rows[victim["tile_y"]][victim["tile_x"]]
    except (TypeError, KeyError, IndexError):
        pass
    return {"attacker": instruction["unit_object"], "weapon": instruction["attack"]["weapon"],
            "slot": instruction["attack"]["slot"], "power": expect["power"],
            "target": target, "target_mech": victim.get("mech_id"),
            "target_pilot": victim.get("pilot_id"), "target_hp_before": victim.get("hp"),
            "terrain": terrain, "forecast_hit": gate_hit, "deltas": fired.get("deltas", [])}


async def plan_and_act(io: act.ActIO, policy: Policy, unit_object: int, *,
                       bosses: Collection[int] = frozenset(), min_hit: int = MIN_HIT,
                       hits: Mapping[int, int] | None = None,
                       damage_log: Path | None = None,
                       boss_names: Collection[str] | None = None,
                       boss_factor: float = BOSS_HP_FACTOR,
                       mech_names: dict[int, str] | None = None,
                       settle_first: bool = False,
                       protected: Collection[int] = frozenset(),
                       spirit_skip: set[str] | None = None,
                       foe_reach: dict[int, int] | None = None) -> dict[str, Any]:
    """One planned, gated attack for `unit_object`.

    A `protected` unit (M12: an ally lost in an earlier attempt) is left alone with no input: it
    stays unmoved, which is the MVP Standby, and the turn counts it as skipped.

    With `boss_names` (or `non_boss_first`, which defaults them to `tactics.BOSS_NAMES`) the
    living foes' mech names are read once into `mech_names` (a per-trial cache) and
    `tactics.boss_objects` adds the named and high-max-HP foes to `bosses` (`boss_factor` 0:
    the named ones only).

    Never raises for game, read or input problems: an exception would make the handoff disable
    itself with the emulator on an open menu, so every failure becomes a report.
    """
    if unit_object in protected:
        return {"ok": False, "phase": "handover", "reason": "protected", "moved": False}
    notes: dict[str, Any] = {}
    try:
        if settle_first:
            # The previous act left a story dialogue on screen (its attack was done).
            notes["dialogue_settled"] = await act.settle_dialogue(io, reserve=OVERLAY_NEEDS)
            settled = notes["dialogue_settled"]
            if not settled["settled"]:
                # Progress made: the next call goes on with a fresh budget (the turn waits).
                phase = "dialogue_pending" if settled["presses"] else "failed"
                return {"ok": False, "phase": phase, "stage": "dialogue",
                        "reason": "dialogue_not_finished", "moved": False, **notes}
        if boss_names is None and policy.non_boss_first:
            boss_names = BOSS_NAMES
        if boss_names is not None:
            if mech_names is None:
                mech_names = {}
            bosses = set(bosses) | await _bosses(
                io, boss_names, mech_names,
                foe_reach if policy.max_foes_in_reach is not None else None, boss_factor)
        answer = await _plan_and_act(io, policy, unit_object, bosses, min_hit, hits, damage_log,
                                     notes, spirit_skip, foe_reach, mech_names)
    except act.ActIOError as exc:
        answer = {"ok": False, "phase": "failed", "stage": "io", "reason": f"io_error: {exc}"}
    except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
        answer = {"ok": False, "phase": "failed", "stage": "unexpected",
                  "reason": f"unexpected_data: {exc!r}"}
    return {**answer, **notes}


async def _cast(io: act.ActIO, state: Mapping[str, Any], unit_object: int,
                mech_name: object, spirit_skip: set[str] | None = None) -> dict[str, Any]:
    """Sense or Focus before the attack; an IO without the spirit reads skips it."""
    if not all(hasattr(io, name) for name in ("spirits", "spirit_cursor_bytes",
                                              "command_menu")):
        return {"status": "skipped", "reason": "no_spirit_reader"}
    unit = next((u for u in state.get("units", []) if u.get("object") == unit_object), None)
    if unit is None:
        return {"status": "skipped", "reason": "unit_not_found"}
    return await spirit_cast.cast_before_attack(
        cast(spirit_cast.SpiritIO, io), unit_object, (unit["tile_x"], unit["tile_y"]),
        mech_name=mech_name if isinstance(mech_name, str) else None, reserve=REPLAN_NEEDS,
        skip_mechs=spirit_skip)


async def _safety_facts(io: act.ActIO, policy: Policy, state: Mapping[str, Any],
                        unit_object: int) -> tuple[int | None, Mapping[str, Any] | None]:
    """(turn, pilot spirit read) for the M16 clauses; the pilot is None when not needed or
    unreadable."""
    field = state.get("turn")
    turn = field.get("turn") if isinstance(field, Mapping) else None
    turn = turn if type(turn) is int else None
    # Focus/Sense only matter for the turn-1 hold (an unknown turn counts as turn 1).
    if not policy.hold_unspirited_turn_one or (turn is not None and turn > 1):
        return turn, None
    reader = getattr(io, "spirits", None)
    try:
        pilot = await reader(unit_object) if reader is not None else None
    except act.ActIOError:
        pilot = None
    return turn, pilot if isinstance(pilot, Mapping) else None


async def _protected(io: act.ActIO, policy: Policy, state: Mapping[str, Any], unit_object: int,
                     pilot: Mapping[str, Any] | None, mech_name: object, notes: dict[str, Any],
                     spirit_skip: set[str] | None) -> bool:
    """M16 turn-1 test. Without the spirit clause a learned Focus/Sense is enough. With it
    (3 Nov, run m16-a: a skipped Sense let Michel's VF-25G advance into a counter) the pilot counts
    only with Focus/Sense already active, or once one is cast here, before any move."""
    if pilot is None or not spirited(pilot):
        return False
    if not policy.spirit_before_attack:
        return True
    unit: Mapping[str, Any] = next(
        (u for u in state.get("units", []) if u.get("object") == unit_object), {})
    hp, max_hp = unit.get("hp"), unit.get("max_hp")
    if type(hp) is int and type(max_hp) is int and hp * 100 < policy.heal_below_percent * max_hp:
        return False                    # it hands over `retreat_needed`: no SP spent first
    if set(pilot.get("active") or ()) & set(SAFE_SPIRITS):
        return True
    choice = choose_spirit(pilot)
    if choice is None or choice["spirit"] not in SAFE_SPIRITS:
        return False
    notes["spirit"] = await _cast(io, state, unit_object, mech_name, spirit_skip)
    return bool(notes["spirit"].get("status") == "cast"
                and notes["spirit"].get("spirit") in SAFE_SPIRITS)


def _cast_stop(cast_result: Mapping[str, Any]) -> str | None:
    """Why play must stop after a cast attempt, or None."""
    if cast_result.get("status") == "mismatch":
        return "spirit_mismatch"
    if cast_result.get("on_map") is False:          # never act on an unknown screen
        return "spirit_menus_not_closed"
    return None


async def _advance(io: act.ActIO, state: Mapping[str, Any], plan: Mapping[str, Any],
                   instruction: Mapping[str, Any]) -> dict[str, Any]:
    """M16: move toward the foes with no attack, then Standby on the post-move menu."""
    moved = await act.run_act(instruction, io)
    if not moved.get("ok"):
        stages: list[Mapping[str, Any]] = moved.get("stages", [])  # type: ignore[assignment]
        landed = (any(st.get("stage") == "move" for st in stages)
                  or _moved_elsewhere(moved, state, instruction["unit_object"]))
        failed: dict[str, Any] = {"ok": False, "phase": "failed", "plan": plan, "outcome": moved,
                                  "moved": landed}
        if landed:
            failed["standby"] = await _standby(io, instruction["unit_object"])
        return failed
    standby = await _standby(io, instruction["unit_object"])
    return {"ok": True, "phase": "advanced", "plan": plan, "outcome": moved, "moved": True,
            "standby": standby}


def _moved_elsewhere(outcome: Mapping[str, Any], state: Mapping[str, Any],
                     unit_object: int) -> bool:
    """An unconfirmed Move that still left the unit on another tile (post-move menu up)."""
    facts: Mapping[str, Any] = outcome.get("facts") or {}
    units: list[Mapping[str, Any]] = state.get("units", [])
    unit: Mapping[str, Any] = next((u for u in units if u.get("object") == unit_object), {})
    start = [unit.get("tile_x"), unit.get("tile_y")]
    return (outcome.get("stage") == "move" and outcome.get("reason") == "move_not_confirmed"
            and facts.get("tile") is not None and None not in start
            and facts.get("tile") != start)


def _over_cursor_budget(io: act.ActIO, state: Mapping[str, Any], instruction: Mapping[str, Any],
                        *, spirit: bool) -> bool:
    """M15: the planned walks (unit -> destination -> target) would overrun the turn's cursor
    budget; an IO without the budget reader, or an unreadable tile, never refuses here."""
    left = getattr(io, "cursor_presses_left", None)
    units = {u.get("object"): u for u in state.get("units", []) if isinstance(u, Mapping)}
    unit = units.get(instruction.get("unit_object"))
    attack = instruction.get("attack")
    foe = units.get((attack or {}).get("target_object"))
    if left is None or unit is None or (foe is None and attack is not None):
        return False
    move_to = instruction.get("move_to")
    cost = press_budget.act_cost(
        (unit["tile_x"], unit["tile_y"]),
        destination=(move_to[0], move_to[1]) if move_to else None,
        target=(foe["tile_x"], foe["tile_y"]) if foe is not None else None, spirit=spirit)
    return cost > int(left())


async def _read_foe(io: act.ActIO, obj: int, names: dict[int, str] | None,
                    reach: dict[int, int] | None) -> None:
    """One weapon read fills both per-trial caches (boss names, M16 reach); a failed read leaves
    the foe out (`tactics` then treats its reach as every tile)."""
    try:
        read = await io.read_weapons(obj)
    except act.ActIOError:
        return
    if names is not None:
        names[obj] = str(read.get("mech_name", ""))
    value = foe_reach_of(read)
    if reach is not None and value is not None:
        reach[obj] = value


async def _foe_reach(io: act.ActIO, state: Mapping[str, Any], cache: dict[int, int] | None,
                     names: dict[int, str] | None = None) -> dict[int, int]:
    """Reach of every living foe (M16), read once per trial into `cache`."""
    cache = {} if cache is None else cache
    for unit in state.get("units", []):
        obj = unit.get("object")
        if (targets.is_foe(unit.get("raw_menu_group_byte")) and type(obj) is int
                and obj not in cache):
            await _read_foe(io, obj, names, cache)
    return cache


async def _bosses(io: act.ActIO, names: Collection[str], cache: dict[int, str],
                  reach: dict[int, int] | None = None,
                  factor: float = BOSS_HP_FACTOR) -> frozenset[int]:
    """Named or high-max-HP foes; a foe whose name cannot be read counts by max HP only."""
    state = await io.state()
    units: list[Mapping[str, Any]] = state.get("units", [])     # type: ignore[assignment]
    for unit in units:
        obj = unit.get("object")
        if (targets.is_foe(unit.get("raw_menu_group_byte")) and type(obj) is int
                and obj not in cache):
            await _read_foe(io, obj, cache, reach)
    return boss_objects(units, cache, names, factor)


async def _plan_and_act(io: act.ActIO, policy: Policy, unit_object: int,
                        bosses: Collection[int], min_hit: int, hits: Mapping[int, int] | None,
                        damage_log: Path | None, notes: dict[str, Any],
                        spirit_skip: set[str] | None = None,
                        foe_reach: dict[int, int] | None = None,
                        mech_names: dict[int, str] | None = None) -> dict[str, Any]:
    state = await io.state()
    weapons = await io.read_weapons(unit_object)
    reach = (await _foe_reach(io, state, foe_reach, mech_names)
             if policy.max_foes_in_reach is not None or policy.retreat_damaged else None)
    excluded: list[int] = []
    turn, pilot = await _safety_facts(io, policy, state, unit_object)
    is_spirited = await _protected(io, policy, state, unit_object, pilot,
                                   weapons.get("mech_name"), notes, spirit_skip)
    if "spirit" in notes:
        stop = _cast_stop(notes["spirit"])
        if stop is not None:
            return {"ok": False, "phase": "failed", "stage": "spirit", "reason": stop,
                    "moved": False}
    # No Spirit presses are reserved for a mech already known to have no usable layout.
    tries_spirit = policy.spirit_before_attack and not (
        spirit_skip is not None and weapons.get("mech_name") in spirit_skip)
    while True:
        plan = plan_attack(state, weapons, policy, unit_object, bosses=bosses, hits=hits,
                           exclude=excluded, turn=turn, spirited=is_spirited, foe_reach=reach)
        if plan.get("reason") == "no_target" and io.time_left() >= OVERLAY_NEEDS:
            plan = plan_attack(await _open_move_range(io, unit_object), weapons, policy,
                               unit_object, bosses=bosses, hits=hits, exclude=excluded,
                               turn=turn, spirited=is_spirited, foe_reach=reach)
        # M16 (m16-i): a damaged unit casts Focus/Sense before it moves away or stays; a retreat
        # move is checked against the cursor budget first, so a refusal presses nothing.
        planned = plan.get("expect")
        retreat = plan.get("reason") == "retreat_stay" or (
            isinstance(planned, Mapping) and planned.get("rule") == "retreat")
        casts = retreat and policy.spirit_before_attack and "spirit" not in notes
        if casts and "act" in plan and _over_cursor_budget(
                io, state, plan["act"], spirit=tries_spirit):    # type: ignore[arg-type]
            return {"ok": False, "phase": "handover", "reason": "cursor_budget", "plan": plan,
                    "moved": False}
        if casts:
            notes["spirit"] = await _cast(io, state, unit_object, weapons.get("mech_name"),
                                          spirit_skip)
            stop = _cast_stop(notes["spirit"])
            if stop is not None:
                return {"ok": False, "phase": "failed", "stage": "spirit", "reason": stop,
                        "plan": plan, "moved": False}
        if "handover" in plan:
            return {"ok": False, "phase": "handover", "reason": plan["reason"],
                    **({"excluded": excluded} if excluded else {})}
        instruction: dict[str, Any] = plan["act"]       # type: ignore[assignment]
        moved = bool(instruction.get("move_to"))
        if _over_cursor_budget(io, state, instruction, spirit=(
                tries_spirit and "spirit" not in notes and "attack" in instruction)):
            return {"ok": False, "phase": "handover", "reason": "cursor_budget", "plan": plan,
                    "moved": False}
        if "attack" not in instruction:
            return await _advance(io, state, plan, instruction)
        if policy.spirit_before_attack and "spirit" not in notes:
            notes["spirit"] = await _cast(io, state, unit_object, weapons.get("mech_name"),
                                          spirit_skip)
            stop = _cast_stop(notes["spirit"])
            if stop is not None:
                return {"ok": False, "phase": "failed", "stage": "spirit", "reason": stop,
                        "plan": plan, "moved": False}
        first = await act.run_act(instruction, io, commit=False)
        failed_at = first.get("stage")
        # The game can refuse a weapon the data allows (22 Oct live: greyed, no enemy in reach).
        # Before any Move the macro backed out cleanly, so plan again without that weapon.
        if (not first.get("ok") and not moved and failed_at in REPLAN_STAGES
                and len(excluded) < MAX_REPLANS and io.time_left() >= REPLAN_NEEDS):
            excluded.append(instruction["attack"]["slot"])
            continue
        break
    expect: dict[str, Any] = plan["expect"]         # type: ignore[assignment]
    extra: dict[str, Any] = {"excluded": excluded} if excluded else {}
    if not first.get("ok"):
        failed: dict[str, Any] = {"ok": False, "phase": "failed", "plan": plan, "outcome": first,
                                  "moved": moved, **extra}
        # After a confirmed Move, a weapon/target/forecast failure backs out to the post-move menu
        # (other stages leave the screen unknown, so nothing more is pressed there).
        stages: list[Mapping[str, Any]] = first.get("stages", [])  # type: ignore[assignment]
        # A Move that landed on another tile also leaves the post-move menu up (31 Oct live,
        # m14s33h); `_standby` presses only once its own menu read shows that menu.
        elsewhere = _moved_elsewhere(first, state, unit_object)
        if ((moved and failed_at in REPLAN_STAGES
             and any(s.get("stage") == "move" for s in stages)) or elsewhere):
            failed["standby"] = await _standby(io, unit_object)
        return failed
    # Menus open at the forecast: select, [attack menu], weapon list and forecast (a Move closes
    # the select level). A Move cannot be undone: the unit stays on the new tile.
    open_menus = 3 if moved else 4
    if notes.get("spirit", {}).get("status") == "cast":
        expect = {**expect, "hit": None}            # Sense/Focus change the hit chance
    reason = forecast_gate(instruction, first, expect, min_hit)
    if reason is None and io.time_left() < act.FIRE_NEEDS:
        reason = "no_time_to_fire"
    if reason is not None:
        closed = await _back_out(io, open_menus)
        declined: dict[str, Any] = {"ok": False, "phase": "declined", "reason": reason,
                                    "plan": plan, "forecast": first.get("forecast"),
                                    "moved": moved, "back_out_failed": not closed, **extra}
        if moved and closed:
            declined["standby"] = await _standby(io, unit_object)
        return declined
    fired = await act.run_act(instruction, io, phase="fire")
    if not fired.get("ok"):
        return {"ok": False, "phase": "failed", "plan": plan, "outcome": fired, "moved": moved}
    forecast: dict[str, Any] = first["forecast"]     # type: ignore[assignment]
    answer: dict[str, Any] = {"ok": True, "phase": "fired", "plan": plan, "forecast": forecast,
                              "outcome": fired, "moved": moved, **extra}
    if damage_log is not None:
        # The attack already happened: a logging problem is reported next to the result.
        try:
            record = _damage_record(plan, forecast["hit"], fired, state)
            with damage_log.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except (OSError, KeyError, TypeError, ValueError) as exc:
            answer["log_error"] = repr(exc)
    return answer
