"""End Turn and the enemy phase (M10): open the system menu, confirm End Turn, then advance with
Circle only until the next player phase has started.

Known from the 19 Oct trial (docs/progress.md, "Short-term B"): Circle on an empty map tile opens
the system menu with EndTurn highlighted; Circle on EndTurn asks "Unmoved Units: N - End phase?" and
Circle answers Yes; the enemy phase runs by itself and stops at each enemy attack's forecast with
Start highlighted, which Circle also takes (the game's default defender choice). The turn counter
reads T through the enemy phase and T+1 once the player phase starts; allies then read unmoved.
Only Circle is pressed after the confirmation, never while turn T+1 is on screen. Every stop is a
result, never an exception: the helper would disable itself with the game mid-phase.

M16 Evade (user, 3 Nov: above 30% foe hit choose Eva.; recon m16-rec-enemy): each enemy attack
shows the forecast window FORECAST_WINDOW with Start / Anim / Support (greyed: skipped) / Move, its
cursor at FORECAST_CURSOR (0 Start, 3 Move). Move opens SELECT-ACTION (ACTION_WINDOW) Atk. / Def. /
Eva., cursor at ACTION_CURSOR; Eva. halves the hover hit (35 -> 17) and the cursor returns to
Start. With `evade_above`, a forecast whose hit is above it gets Down to Move, Circle, Down to Eva.,
Circle, each step read back from memory; a lower hit afterwards confirms it. Directions are pressed
only on a forecast; a cursor that does not follow is walked back (stop when it cannot be).
M16 Def. (user, 3 Nov, run m16-i: Eva. left a 100% hit at 100%): with `defend_at`, a hit at or above
it gets Move > Def. (DEFEND_ROW) instead; Def. does not change the hit, so reaching Def. and the
forecast coming back on Start confirm it.
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
RESET_POLLS = 20               # turn T+1 seen: reads to wait for the allies to reset
LOSSES = ("ally_destroyed", "unit_lost")   # stops the agent may accept (user decision, 23 Oct)
FORECAST_WINDOW, ACTION_WINDOW = 0x08E4C81C, 0x08E4CD80      # UI-pool windows (m16-rec-enemy)
FORECAST_CURSOR, ACTION_CURSOR = 0x08E4C898, 0x08E4CDB8      # u32 menu rows
MOVE_ROW, DEFEND_ROW, EVADE_ROW = 3, 1, 2
REACTION_PAUSE = 0.4


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
    """Per-unit HP/EN changes since End Turn (units that appeared are listed with hp [None, hp];
    living units gone from the list, as destroyed units are live, with hp [hp, None] and lost)."""
    before = {u["object"]: u for u in _units(start)}
    now = _units(state)
    present = {u["object"] for u in now}
    changes: list[dict[str, Any]] = []
    for u in now:
        old = before.get(u["object"], {})
        entry: dict[str, Any] = {"object": u["object"], "group": u["raw_menu_group_byte"]}
        for key in ("hp", "en"):
            if old.get(key) != u.get(key):
                entry[key] = [old.get(key), u.get(key)]
        if len(entry) > 2:
            changes.append(entry)
    changes += [{"object": obj, "group": u["raw_menu_group_byte"], "hp": [u["hp"], None],
                 "lost": True} for obj, u in before.items() if obj not in present and u["hp"] > 0]
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
        self.reactions: list[dict[str, Any]] = []   # M16: one per enemy forecast with a limit
        self.reacted_at = -1                       # presses when the current forecast was handled

    def result(self, phase: str, **extra: Any) -> dict[str, Any]:
        ok = phase in ("done", "continue", "window")
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


async def _new_turn(io: ActIO, phase: Phase, state: Mapping[str, Any]) -> dict[str, Any]:
    """Turn T+1 is up: never press again; done once the allies read unmoved twice in a row."""
    good = scenes = 0
    for _ in range(RESET_POLLS):
        if state is SCENE:
            good, scenes = 0, scenes + 1
            if scenes >= 2:
                phase.stopped = "scene_at_new_turn"     # a turn-start event: the agent looks first
                return phase.result("stopped")
        else:
            scenes = 0
            good = good + 1 if finished(phase.start, state) else 0
            if good >= 2:
                phase.done = True
                return phase.result("done")
        await io.sleep(SETTLE_PAUSE)
        nxt = await _read(io, phase)
        if nxt is None:
            return phase.result("stopped")
        state = nxt
    phase.stopped = "player_phase_unclear"
    return phase.result("stopped")


async def advance(io: ActIO, phase: Phase, *, accept_losses: bool = False,
                  stop_at_window: bool = False, evade_above: int | None = None,
                  defend_at: int | None = None) -> dict[str, Any]:
    """Circle until turn T+1 has started, a stop, or this call's cap (then "continue").

    `stop_at_window` (M16 recon): after this call's first Circle, return phase "window" as soon
    as the UI pool shows any window on a readable map (an enemy-attack forecast), pressing nothing.

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
            if phase.scene_run == 1:
                # One unreadable read may be a camera pan over the turn T+1 map: read again
                # before any Circle.
                await io.sleep(SETTLE_PAUSE)
                continue
            if phase.scene_run > SCENE_PRESSES + 1:
                phase.stopped = "scene_too_long"
                return phase.result("stopped")
        else:
            phase.scene_run = 0
        if not scene and turn_of(state) == phase.turn0 + 1:
            return await _new_turn(io, phase, state)
        if (stop_at_window and pressed and not scene
                and state.get("screen") not in (None, "no_menu")):
            return phase.result("window", screen=state.get("screen"),
                                ui_windows=state.get("ui_windows"))
        if phase.presses >= PHASE_PRESSES or phase.clock() - phase.started > PHASE_SECONDS:
            phase.stopped = "phase_budget"
            return phase.result("stopped")
        if pressed >= CALL_PRESSES or io.time_left() < CALL_NEEDS:
            return phase.result("continue")
        if ((evade_above is not None or defend_at is not None) and not scene
                and _forecast(state) and phase.reacted_at != phase.presses):
            phase.reacted_at = phase.presses
            note = await _react(io, evade_above, defend_at)
            phase.reactions.append(note)
            if note["action"] == "failed":
                phase.stopped = "reaction_failed"
                return phase.result("stopped")
        try:
            await io.press("circle", 2)
        except ActIOError as exc:
            phase.stopped = f"io_error: {exc}"
            return phase.result("stopped")
        pressed += 1
        phase.presses += 1
        phase.scene_presses += scene
        await io.sleep(ADVANCE_PAUSE)


def _forecast(state: Mapping[str, Any]) -> bool:
    windows = state.get("ui_windows")
    return (isinstance(windows, list) and FORECAST_WINDOW in windows
            and ACTION_WINDOW not in windows)


async def _rows(io: ActIO) -> tuple[int, int] | None:
    reader = getattr(io, "reaction_cursors", None)
    if reader is None:
        return None
    try:
        rows: tuple[int, int] = await reader()
    except ActIOError:
        return None
    return rows


async def _walk(io: ActIO, index: int, wanted: int, presses: int) -> bool:
    """Down (or Up) until the menu row `index` of `reaction_cursors` reads `wanted`."""
    for _ in range(presses + 1):
        rows = await _rows(io)
        if rows is None:
            return False
        if rows[index] == wanted:
            return True
        await io.press("down" if rows[index] < wanted else "up", 2)
        await io.sleep(REACTION_PAUSE)
    return False


async def _react(io: ActIO, evade_above: int | None,
                 defend_at: int | None = None) -> dict[str, Any]:
    """Def. at or above `defend_at`, else Eva. above `evade_above`; the forecast stays up with Start
    highlighted."""
    try:
        before = await io.hit()
        hit = before.get("hit")
        if before.get("state") != "hit" or type(hit) is not int:
            return {"hit": None, "action": "skipped", "reason": "hit_unreadable"}
        if defend_at is not None and hit >= defend_at:
            action, row = "defend", DEFEND_ROW
        elif evade_above is not None and hit > evade_above:
            action, row = "evade", EVADE_ROW
        else:
            return {"hit": hit, "action": "default"}
        rows = await _rows(io)
        if rows is None or rows[0] != 0:
            return {"hit": hit, "action": "skipped",
                    "reason": "no_reader" if rows is None else "cursor_not_on_start"}
        if not await _walk(io, 0, MOVE_ROW, 3):
            # Walk back to Start; Circle there is the default answer.
            if await _walk(io, 0, 0, 3):
                return {"hit": hit, "action": "skipped", "reason": "move_not_reached"}
            return {"hit": hit, "action": "failed", "reason": "move_not_reached"}
        await io.press("circle", 2)
        await io.sleep(REACTION_PAUSE)
        windows = (await io.state()).get("ui_windows")
        if not (isinstance(windows, list) and ACTION_WINDOW in windows):
            return {"hit": hit, "action": "failed", "reason": "action_menu_not_open"}
        if not await _walk(io, 1, row, 2):
            return {"hit": hit, "action": "failed", "reason": f"{action}_not_reached"}
        await io.press("circle", 2)
        await io.sleep(REACTION_PAUSE)
        rows = await _rows(io)
        after = await io.hit()
        if rows is None or rows[0] != 0 or not _forecast(await io.state()):
            return {"hit": hit, "action": "failed", "reason": "forecast_not_back"}
    except ActIOError as exc:
        return {"hit": None, "action": "failed", "reason": f"io_error: {exc}"}
    later = after.get("hit")
    return {"hit": [hit, later], "action": action,
            "confirmed": action == "defend" or (isinstance(later, int) and later < hit)}


def report(phase: Phase) -> dict[str, Any]:
    """Serialisable enemy-phase summary (enemy-phase-report.json)."""
    answer = phase.result("done" if phase.done else "stopped" if phase.stopped else "continue")
    hurt = [d["object"] for d in answer["deltas"] if d["group"] == ALLY_GROUP and "hp" in d
            and isinstance(d["hp"][0], int) and isinstance(d["hp"][1], int)
            and d["hp"][1] < d["hp"][0]]
    destroyed = [d["object"] for d in answer["deltas"]
                 if d.get("lost") or ("hp" in d and d["hp"][1] == 0)]
    return {"turn": answer["turn"], "done": phase.done, "stopped": phase.stopped,
            "presses": phase.presses, "scene_presses": phase.scene_presses,
            "calls": phase.calls, "damaged_allies": hurt,
            "destroyed": destroyed, "losses": {str(k): v for k, v in phase.losses.items()},
            "deltas": answer["deltas"], "screens": list(phase.screens),
            "reactions": list(phase.reactions)}
