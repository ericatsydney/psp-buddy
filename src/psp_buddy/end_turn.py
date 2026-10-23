"""End Turn and the enemy phase (M10): open the system menu, confirm End Turn, then advance with
Circle only until the next player phase has started.

Known from the 19 Oct trial (docs/progress.md, "Short-term B"): Circle on an empty map tile opens
the system menu with EndTurn highlighted; Circle on EndTurn asks "Unmoved Units: N - End phase?" and
Circle answers Yes; the enemy phase runs by itself and stops at each enemy attack's forecast with
Start highlighted, which Circle also takes (the game's default defender choice). The turn counter
reads T through the enemy phase and T+1 once the player phase starts; allies then read unmoved.
Only Circle is pressed after the confirmation, never while turn T+1 is on screen. Every stop is a
result, never an exception: the helper would disable itself with the game mid-phase.
"""

import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .act import ActIO, ActIOError

ALLY_GROUP = 0
MENU_PAUSE = 0.8
CONFIRM_PAUSE = 1.5
ADVANCE_PAUSE = 2.5            # one Circle, then let the battle or message play
SETTLE_PAUSE = 1.0             # between the two reads that confirm the new player phase
CALL_PRESSES = 40              # per call: the helper's hard cancel is 120 s
CALL_NEEDS = 8.0               # seconds a press, a pause and a read take
PHASE_PRESSES = 300            # whole enemy phase (19 Oct: 7 presses; 23 Oct: long story event)
SCENE_PRESSES = 60             # Circles in a row while the map state is unreadable (a scene;
                               # 23 Oct live: more than 19 dialogue lines in one event)
PHASE_SECONDS = 900.0
RESET_POLLS = 10               # turn T+1 seen: wait this many reads for the allies to reset
LOSSES = ("ally_destroyed", "unit_lost")   # stops the agent may accept (user decision, 23 Oct)


def _units(state: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    units = state.get("units")
    if not isinstance(units, list) or not units:
        raise ValueError("state has no units")
    for u in units:
        if (type(u.get("object")) is not int or type(u.get("hp")) is not int
                or type(u.get("raw_menu_group_byte")) is not int):
            raise ValueError("unit with unreadable fields")
    return units


def turn_of(state: Mapping[str, Any]) -> int:
    turn = state.get("turn")
    value = turn.get("turn") if isinstance(turn, Mapping) else None
    if type(value) is not int:
        raise ValueError("turn counter unreadable")
    return value


def _allies(units: Sequence[Mapping[str, Any]]) -> dict[int, Mapping[str, Any]]:
    return {u["object"]: u for u in units if u["raw_menu_group_byte"] == ALLY_GROUP}


def empty_tile(state: Mapping[str, Any]) -> list[int] | None:
    """The map tile nearest the cursor with no living unit on it (ties: top row, then left)."""
    grid, cursor = state.get("map"), state.get("cursor")
    if not isinstance(grid, Mapping) or not isinstance(cursor, Mapping):
        return None
    width, height, cx, cy = grid.get("width"), grid.get("height"), cursor.get("x"), cursor.get("y")
    if not all(type(v) is int for v in (width, height, cx, cy)):
        return None
    assert isinstance(width, int) and isinstance(height, int)
    assert isinstance(cx, int) and isinstance(cy, int)
    taken = {(u.get("tile_x"), u.get("tile_y")) for u in _units(state) if u["hp"] > 0}
    free = [(abs(x - cx) + abs(y - cy), y, x) for y in range(height) for x in range(width)
            if (x, y) not in taken]
    if not free:
        return None
    _, y, x = min(free)
    return [x, y]


def losses(start: Mapping[str, Any], state: Mapping[str, Any]) -> dict[int, str]:
    """Allies alive at End Turn that are now destroyed (HP 0) or gone from the unit list."""
    before, now = _allies(_units(start)), _allies(_units(state))
    found: dict[int, str] = {}
    for obj, ally in before.items():
        if ally["hp"] <= 0:
            continue
        if obj not in now:
            found[obj] = "unit_lost"
        elif now[obj]["hp"] <= 0:
            found[obj] = "ally_destroyed"
    return found


def check(start: Mapping[str, Any], state: Mapping[str, Any]) -> str | None:
    """A stop reason, or None. Foes destroyed by counters are reported, not stops."""
    try:
        turn0, turn = turn_of(start), turn_of(state)
        lost = losses(start, state)
    except ValueError:
        return "unknown_state"
    if turn < turn0:
        return "stage_restart"         # 23 Oct live: a lose condition sent the stage back to turn 1
    if turn > turn0 + 1:
        return "turn_jump"
    return next(iter(lost.values()), None)


def finished(start: Mapping[str, Any], state: Mapping[str, Any]) -> bool:
    """Turn T+1 has started: the counter moved on and every living ally reads unmoved."""
    try:
        if turn_of(state) != turn_of(start) + 1:
            return False
        living = [u for u in _allies(_units(state)).values() if u["hp"] > 0]
    except ValueError:
        return False
    return bool(living) and all(u.get("counted_as_unmoved") is True for u in living)


def deltas(start: Mapping[str, Any], state: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Per-unit HP/EN changes since End Turn (units that appeared are listed with hp [None, hp])."""
    before = {u["object"]: u for u in _units(start)}
    changes: list[dict[str, Any]] = []
    for u in _units(state):
        old = before.get(u["object"], {})
        entry: dict[str, Any] = {"object": u["object"], "group": u["raw_menu_group_byte"]}
        for key in ("hp", "en"):
            if old.get(key) != u.get(key):
                entry[key] = [old.get(key), u.get(key)]
        if len(entry) > 2:
            changes.append(entry)
    return changes


class Phase:
    """Bookkeeping of one End Turn across `advance` calls."""

    def __init__(self, start: Mapping[str, Any], *,
                 clock: Callable[[], float] = time.monotonic) -> None:
        _units(start)
        self.turn0 = turn_of(start)
        self.start = start
        self.clock = clock
        self.confirmed = False
        self.started = 0.0
        self.presses = 0
        self.calls = 0
        self.done = False
        self.stopped: str | None = None
        self.accept_losses = False
        self.losses: dict[int, str] = {}       # accepted ally losses (object -> reason)
        self.scene_run = 0                     # unreadable reads in a row (story scene)
        self.scene_presses = 0
        self.last: Mapping[str, Any] = start
        self.screens: list[str] = []

    def result(self, phase: str, **extra: Any) -> dict[str, Any]:
        ok = phase in ("done", "continue")
        try:
            turn = turn_of(self.last)
            changes = deltas(self.start, self.last)
        except ValueError:
            turn, changes = None, []
        return {"ok": ok, "phase": phase, "turn": [self.turn0, turn], "presses": self.presses,
                "deltas": changes, **({"reason": self.stopped} if self.stopped else {}), **extra}


async def open_menu(io: ActIO, state: Mapping[str, Any]) -> dict[str, Any]:
    """Walk the cursor to an empty tile and press Circle once (the system menu opens there)."""
    try:
        turn = turn_of(state)
        tile = empty_tile(state)
    except ValueError:
        return {"ok": False, "phase": "stopped", "reason": "unknown_state"}
    if tile is None:
        return {"ok": False, "phase": "stopped", "reason": "no_empty_tile"}
    try:
        walk = await io.goto(tile)
        if not walk.get("reached"):
            return {"ok": False, "phase": "stopped", "reason": "cursor_did_not_reach_tile",
                    "walk": dict(walk)}
        await io.press("circle", 2)
        await io.sleep(MENU_PAUSE)
    except ActIOError as exc:
        return {"ok": False, "phase": "stopped", "reason": f"io_error: {exc}"}
    return {"ok": True, "phase": "menu_open", "tile": tile, "turn": turn}


async def confirm(io: ActIO, phase: Phase) -> dict[str, Any]:
    """Circle on the highlighted EndTurn, then Circle on "End phase? Yes"."""
    try:
        await io.press("circle", 2)
        phase.confirmed = True                 # from here on only Circle moves the game on
        phase.started = phase.clock()
        await io.sleep(CONFIRM_PAUSE)
        await io.press("circle", 2)
        await io.sleep(CONFIRM_PAUSE)
    except ActIOError as exc:
        phase.stopped = f"io_error: {exc}"
        return phase.result("stopped")
    return {"ok": True, "phase": "ending", "turn": phase.turn0}


SCENE: Mapping[str, Any] = {}      # marker: the map state is not readable (a story scene)


async def _read(io: ActIO, phase: Phase) -> Mapping[str, Any] | None:
    """The state, SCENE when it cannot be read (23 Oct live: a story dialogue on a zoomed view
    refuses the map read), or None after a stop."""
    try:
        state = await io.state()
    except ActIOError:
        return SCENE
    reason = check(phase.start, state)
    if reason != "unknown_state":
        phase.last = state             # the report shows the state that caused a stop
    if reason in LOSSES and phase.accept_losses:
        phase.losses.update(losses(phase.start, state))
        reason = None
    if reason:
        phase.stopped = reason
        return None
    return state


async def advance(io: ActIO, phase: Phase, *, accept_losses: bool = False) -> dict[str, Any]:
    """Circle until turn T+1 has started, a stop, or this call's cap (then "continue").

    With `accept_losses` a destroyed or lost ally is recorded in `phase.losses` instead of
    stopping, and a phase stopped only by such a loss resumes; nothing else is excused, and an
    unreadable scene after a loss stops at once (it may be the defeat sequence).
    """
    if phase.done:
        return phase.result("done")
    if accept_losses:
        phase.accept_losses = True
        if phase.stopped in LOSSES:
            phase.stopped = None
    if phase.stopped or not phase.confirmed:
        phase.stopped = phase.stopped or "not_confirmed"
        return phase.result("stopped")
    phase.calls += 1
    pressed = 0
    while True:
        state = await _read(io, phase)
        if state is None:
            return phase.result("stopped")
        scene = state is SCENE
        if scene and phase.losses:
            # 23 Oct live: after accepted losses the dialogue was the stage's defeat sequence and
            # blind Circles took the default retry. Never advance a scene after a loss.
            phase.stopped = "scene_after_loss"
            return phase.result("stopped")
        if scene:
            # Decision-free dialogue: advance it with Circle, bounded (user decision, 23 Oct).
            phase.scene_run += 1
            if phase.scene_run > SCENE_PRESSES:
                phase.stopped = "scene_too_long"
                return phase.result("stopped")
        else:
            phase.scene_run = 0
        if not scene and turn_of(state) == phase.turn0 + 1:
            # Turn T+1: never press again; wait for the allies to read unmoved, twice.
            for _ in range(RESET_POLLS):
                if state is not SCENE and finished(phase.start, state):
                    await io.sleep(SETTLE_PAUSE)
                    again = await _read(io, phase)
                    if again is None:
                        return phase.result("stopped")
                    if again is not SCENE and finished(phase.start, again):
                        phase.done = True
                        return phase.result("done")
                    state = again
                    continue
                await io.sleep(SETTLE_PAUSE)
                state = await _read(io, phase)
                if state is None:
                    return phase.result("stopped")
            phase.stopped = "player_phase_unclear"
            return phase.result("stopped")
        if phase.presses >= PHASE_PRESSES or phase.clock() - phase.started > PHASE_SECONDS:
            phase.stopped = "phase_budget"
            return phase.result("stopped")
        if pressed >= CALL_PRESSES or io.time_left() < CALL_NEEDS:
            return phase.result("continue")
        try:
            await io.press("circle", 2)
        except ActIOError as exc:
            phase.stopped = f"io_error: {exc}"
            return phase.result("stopped")
        pressed += 1
        phase.presses += 1
        phase.scene_presses += scene
        await io.sleep(ADVANCE_PAUSE)


def report(phase: Phase) -> dict[str, Any]:
    """Serialisable enemy-phase summary (enemy-phase-report.json)."""
    answer = phase.result("done" if phase.done else "stopped" if phase.stopped else "continue")
    hurt = [d["object"] for d in answer["deltas"] if d["group"] == ALLY_GROUP and "hp" in d
            and isinstance(d["hp"][0], int) and isinstance(d["hp"][1], int)
            and d["hp"][1] < d["hp"][0]]
    destroyed = [d["object"] for d in answer["deltas"] if "hp" in d and d["hp"][1] == 0]
    return {"turn": answer["turn"], "done": phase.done, "stopped": phase.stopped,
            "presses": phase.presses, "scene_presses": phase.scene_presses,
            "calls": phase.calls, "damaged_allies": hurt,
            "destroyed": destroyed, "losses": {str(k): v for k, v in phase.losses.items()},
            "deltas": answer["deltas"], "screens": list(phase.screens)}
