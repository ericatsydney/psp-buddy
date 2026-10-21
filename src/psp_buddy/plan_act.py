"""`plan_and_act`: choose one attack from a policy, run it to the forecast, fire only if it agrees.

Order: read state and weapons, `tactics.plan_attack`; when nothing is in reach from the current
tile, open the unit's Move range once (select, Move, read, back out) and plan again with moves;
`act.run_act(commit=False)` to the forecast; gate; then `phase="fire"` or back out with Cross.
The gate compares what the game shows with what was planned: the same weapon and target, the hit
chance seen when the target was chosen equals the forecast (and the planned one when known), and
the chance is at least `min_hit`. Every fired attack appends the observed deltas to a damage log
so the damage model of docs/research/2026-10-21-damage-model.md can be fitted later.
"""

import json
from collections.abc import Collection, Mapping
from pathlib import Path
from typing import Any

from . import act
from .models import Policy
from .tactics import plan_attack

MIN_HIT = 1
BACK_OUT_PAUSE = 0.6


OVERLAY_NEEDS = act.FIRE_NEEDS + 20.0     # seconds left to open the Move range and still fire


async def _back_out(io: act.ActIO, presses: int) -> bool:
    """Cross out of open menus; False when an input failed (reported, never raised)."""
    try:
        for _ in range(presses):
            await io.press("cross", 2)
            await io.sleep(BACK_OUT_PAUSE)
    except act.ActIOError:
        return False
    return True


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
        return await io.state()
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
                       damage_log: Path | None = None) -> dict[str, Any]:
    """One planned, gated attack for `unit_object`.

    Never raises for game, read or input problems: an exception would make the handoff disable
    itself with the emulator on an open menu, so every failure becomes a report.
    """
    try:
        return await _plan_and_act(io, policy, unit_object, bosses, min_hit, hits, damage_log)
    except act.ActIOError as exc:
        return {"ok": False, "phase": "failed", "stage": "io", "reason": f"io_error: {exc}"}
    except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
        return {"ok": False, "phase": "failed", "stage": "unexpected",
                "reason": f"unexpected_data: {exc!r}"}


async def _plan_and_act(io: act.ActIO, policy: Policy, unit_object: int,
                        bosses: Collection[int], min_hit: int, hits: Mapping[int, int] | None,
                        damage_log: Path | None) -> dict[str, Any]:
    state = await io.state()
    weapons = await io.read_weapons(unit_object)
    plan = plan_attack(state, weapons, policy, unit_object, bosses=bosses, hits=hits)
    if plan.get("reason") == "no_target" and io.time_left() >= OVERLAY_NEEDS:
        plan = plan_attack(await _open_move_range(io, unit_object), weapons, policy,
                           unit_object, bosses=bosses, hits=hits)
    if "handover" in plan:
        return {"ok": False, "phase": "handover", "reason": plan["reason"]}
    instruction: dict[str, Any] = plan["act"]       # type: ignore[assignment]
    expect: dict[str, Any] = plan["expect"]         # type: ignore[assignment]
    moved = bool(instruction.get("move_to"))
    first = await act.run_act(instruction, io, commit=False)
    if not first.get("ok"):
        return {"ok": False, "phase": "failed", "plan": plan, "outcome": first}
    # Menus open at the forecast: select, [attack menu], weapon list and forecast (a Move closes
    # the select level). A Move cannot be undone: the unit stays on the new tile.
    open_menus = 3 if moved else 4
    reason = forecast_gate(instruction, first, expect, min_hit)
    if reason is None and io.time_left() < act.FIRE_NEEDS:
        reason = "no_time_to_fire"
    if reason is not None:
        closed = await _back_out(io, open_menus)
        return {"ok": False, "phase": "declined", "reason": reason, "plan": plan,
                "forecast": first.get("forecast"), "moved": moved, "back_out_failed": not closed}
    fired = await act.run_act(instruction, io, phase="fire")
    if not fired.get("ok"):
        return {"ok": False, "phase": "failed", "plan": plan, "outcome": fired, "moved": moved}
    forecast: dict[str, Any] = first["forecast"]     # type: ignore[assignment]
    answer: dict[str, Any] = {"ok": True, "phase": "fired", "plan": plan, "forecast": forecast,
                              "outcome": fired}
    if damage_log is not None:
        # The attack already happened: a logging problem is reported next to the result.
        try:
            record = _damage_record(plan, forecast["hit"], fired, state)
            with damage_log.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except (OSError, KeyError, TypeError, ValueError) as exc:
            answer["log_error"] = repr(exc)
    return answer
