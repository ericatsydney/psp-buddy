"""Turn bookkeeping for one player phase (pure; M9).

`ready_allies` orders the units still able to act, `TurnLog` classifies every `plan_act` result as
fired, skipped (left as it is, with the reason), standby (moved, could not attack, waited: the
user's MVP rule) or stop (hand over), and `next_unit` / `report`
answer the loop "which unit next, are we done". Nothing here sends input to the game. A unit that
is skipped stays unmoved in memory, so completion means "every ready ally acted or was skipped".
"""

from collections.abc import Mapping
from typing import Any

ALLY_GROUP = 0
FOE_GROUP = 12
SKIP_HANDOVERS = ("no_target", "retreat_needed", "unit_not_ready", "unit_not_ally")
# act stages before the Move and the Start press: a failure there backs out and changes nothing.
BEFORE_ACTION_STAGES = ("plan", "select", "attack_menu", "weapon", "target", "forecast")


def _units(state: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    units = state.get("units")
    if not isinstance(units, list) or not units:
        raise ValueError("state has no units")
    for u in units:
        if (type(u.get("object")) is not int or type(u.get("hp")) is not int
                or type(u.get("tile_x")) is not int or type(u.get("tile_y")) is not int
                or type(u.get("raw_menu_group_byte")) is not int):
            raise ValueError("unit with unreadable fields")
    return units


def ready_allies(state: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Living allies that can still act, nearest to a living foe first (then by object)."""
    units = _units(state)
    foes = [(u["tile_x"], u["tile_y"]) for u in units
            if u["raw_menu_group_byte"] == FOE_GROUP and u["hp"] > 0]

    def distance(u: Mapping[str, Any]) -> int:
        return min((abs(u["tile_x"] - x) + abs(u["tile_y"] - y) for x, y in foes), default=0)

    ready = [u for u in units if u["raw_menu_group_byte"] == ALLY_GROUP and u["hp"] > 0
             and u.get("counted_as_unmoved")]
    return sorted(ready, key=lambda u: (distance(u), u["object"]))


class TurnLog:
    def __init__(self) -> None:
        self.skipped: dict[int, str] = {}
        self.entries: list[dict[str, Any]] = []
        self.stopped: str | None = None

    def record(self, unit_object: int, result: Mapping[str, Any]) -> str:
        """Classify one `plan_act` answer: "fired", "skipped", "standby" or "stop"."""
        outcome, reason = self._classify(result)
        attack = ((result.get("plan") or {}).get("act") or {}).get("attack") or {}
        forecast = result.get("forecast") or {}
        done = result.get("outcome") or {}
        self.entries.append({
            "unit": unit_object, "outcome": outcome, "reason": reason,
            "weapon": attack.get("weapon"), "slot": attack.get("slot"),
            "target": attack.get("target_object"), "hit": forecast.get("hit"),
            "moved": bool(result.get("moved")), "deltas": done.get("deltas", [])})
        if outcome == "skipped":
            self.skipped[unit_object] = str(reason)
        elif outcome == "stop" and self.stopped is None:
            self.stopped = str(reason)
        return outcome

    @staticmethod
    def _reason(result: Mapping[str, Any]) -> str | None:
        reason = result.get("reason")
        inner = result.get("outcome") or {}
        if result.get("phase") == "declined":
            return f"declined:{reason}"
        if reason is None and inner.get("stage"):
            return f"{inner['stage']}:{inner.get('reason')}"
        return reason

    @staticmethod
    def _classify(result: Mapping[str, Any]) -> tuple[str, str | None]:
        phase = result.get("phase")
        reason = result.get("reason")
        if result.get("ok") and phase == "fired":
            return "fired", None
        if phase == "handover":
            return ("skipped", reason) if reason in SKIP_HANDOVERS else ("stop", reason)
        if phase in ("declined", "failed") and result.get("moved") and result.get("standby"):
            return "standby", TurnLog._reason(result)       # moved, then waited (MVP rule)
        if phase == "declined":
            if result.get("back_out_failed"):
                return "stop", "back_out_failed"
            if result.get("moved"):
                return "stop", "declined_after_move"
            return "skipped", f"declined:{reason}"
        if phase == "failed":
            inner = result.get("outcome") or {}
            reason = TurnLog._reason(result)
            moved = bool(((result.get("plan") or {}).get("act") or {}).get("move_to"))
            if inner.get("stage") in BEFORE_ACTION_STAGES and not moved:
                return "skipped", reason
            return "stop", reason or "failed"
        return "stop", f"unexpected_phase:{phase}"


def next_unit(state: Mapping[str, Any], log: TurnLog) -> dict[str, Any]:
    """The next unit to play, how many remain, and whether the turn is done or stopped."""
    base: dict[str, Any] = {"unit_object": None, "remaining": 0, "skipped": dict(log.skipped),
                            "done": False, "stopped": log.stopped}
    if log.stopped is not None:
        return base
    try:
        waiting = [u for u in ready_allies(state) if u["object"] not in log.skipped]
    except ValueError as exc:
        return {**base, "stopped": f"unknown_state: {exc}"}
    if not waiting:
        return {**base, "done": True}
    return {**base, "unit_object": waiting[0]["object"], "remaining": len(waiting)}


def report(log: TurnLog, state: Mapping[str, Any]) -> dict[str, Any]:
    """Serialisable summary of the turn so far."""
    answer = next_unit(state, log)
    turn = state.get("turn")
    try:
        remaining = [u["object"] for u in ready_allies(state) if u["object"] not in log.skipped]
    except ValueError:
        remaining = []
    return {"turn": turn.get("turn") if isinstance(turn, Mapping) else None,
            "fired": sum(e["outcome"] == "fired" for e in log.entries),
            "skipped": dict(log.skipped), "remaining": remaining, "done": answer["done"],
            "stopped": answer["stopped"], "entries": log.entries}
