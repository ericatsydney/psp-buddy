"""The `act` macro: follow one tactical instruction for one ally unit with memory verification.

Stages: plan (pure legality), select, move, attack_menu, weapon, target, forecast, fire, result.
Every stage that sends input is checked from memory (cursor, reachable range, unit tile/EN,
weapon-menu row, hover hit chance, ammo/EN, action-finished counter). Any failed check stops the
macro and reports the stage and reason; menus opened since the last confirmed step are closed
with Cross (harmless on a menu, never used after a confirmed Move).
"""

from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any, Protocol

from . import battle_state, targets

ALLY_GROUP = 0
RESULT_PRESSES = 6
FIRE_POLLS = 16
READ_RETRIES = 6
ANIMATION_SECONDS = 8.0
FIRE_NEEDS = 50.0            # seconds a Start + result needs; less left means stop at the forecast
GUARD_SECONDS = 1.0
MOVE_POLLS = 12
WATCHED = ("hp", "en", "tile_x", "tile_y", "counter_value", "counted_as_unmoved")


class ActIO(Protocol):
    async def press(self, button: str, frames: int = 2) -> None: ...
    async def goto(self, tile: list[int]) -> Mapping[str, object]: ...
    async def state(self) -> Mapping[str, object]: ...
    async def read_weapons(self, unit_object: int) -> Mapping[str, object]: ...
    async def hit(self) -> Mapping[str, object]: ...
    async def menu_row(self) -> tuple[int, int] | None: ...
    async def sleep(self, seconds: float) -> None: ...
    def time_left(self) -> float: ...


MENU_ROW_ADDRESS = 0x08E397A8     # u8 row; the u8 count sits two bytes later (18 Oct dumps)
MENU_ROW_BYTES = 3
MAX_MENU_ROWS = 21


class ActIOError(Exception):
    """A read or input the macro depended on failed; reported as a stage failure."""


def decode_menu_row(blob: bytes) -> tuple[int, int] | None:
    """(row, count) of the open weapon list, or None when the bytes cannot be a list cursor."""
    if len(blob) != MENU_ROW_BYTES:
        raise ValueError("menu row needs 3 bytes")
    row, count = blob[0], blob[2]
    return (row, count) if 0 < count <= MAX_MENU_ROWS and row < count else None


class _Stop(Exception):
    def __init__(self, stage: str, reason: str, facts: dict[str, object] | None = None,
                 retreat: int = 0) -> None:
        super().__init__(reason)
        self.stage, self.reason, self.facts, self.retreat = stage, reason, facts or {}, retreat


def centered(tile: Sequence[int], reachable: Sequence[Sequence[int]]) -> bool:
    """A fresh Move range is centred on the unit; stale costs from another unit fail this."""
    cost = {(x, y): c for x, y, c in reachable}
    near = [pos for pos, c in cost.items() if c == 1]
    return (bool(cost) and (tile[0], tile[1]) not in cost and bool(near)
            and all(abs(x - tile[0]) + abs(y - tile[1]) == 1 for x, y in near)
            and all(c >= abs(x - tile[0]) + abs(y - tile[1]) for (x, y), c in cost.items()))


def _units(state: Mapping[str, object]) -> list[dict[str, object]]:
    units = state.get("units")
    if not isinstance(units, list):
        raise _Stop("plan", "state_has_no_units")
    return [dict(u) for u in units]


def _find(units: Sequence[Mapping[str, object]], unit_object: object) -> dict[str, object] | None:
    found = [dict(u) for u in units if u.get("object") == unit_object]
    return found[0] if len(found) == 1 else None


def _tile(unit: Mapping[str, object]) -> list[int]:
    return [int(unit["tile_x"]), int(unit["tile_y"])]  # type: ignore[call-overload]


def _reachable(state: Mapping[str, object]) -> list[list[int]]:
    raw: Any = state.get("reachable")
    if not raw:
        grid = state.get("map")
        if isinstance(grid, dict):
            raw = [[t["x"], t["y"], t["cost"]]
                   for t in battle_state.reachable_tiles({"cost_rows": grid["cost_rows"]})]
    return [[int(x), int(y), int(c)] for x, y, c in (raw or [])]


def _deltas(before: Sequence[Mapping[str, object]],
            after: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    old = {u["object"]: u for u in before}
    changes: list[dict[str, object]] = []
    for unit in after:
        was = old.get(unit["object"])
        if was is None:
            continue
        diff = {k: [was.get(k), unit.get(k)] for k in WATCHED if was.get(k) != unit.get(k)}
        if diff:
            changes.append({"object": unit["object"], **diff})
    return changes


class _Run:
    def __init__(self, request: Mapping[str, object], io: ActIO) -> None:
        self.io = io
        self.request = request
        self.stages: list[dict[str, object]] = []
        self.depth = 0
        self.current = "plan"
        move = request.get("move_to")
        self.move_to: list[int] | None = [int(n) for n in move] if isinstance(move, list) else None
        attack = request.get("attack")
        self.attack: Mapping[str, object] | None = attack if isinstance(attack, Mapping) else None
        self.state0: Mapping[str, object] = {}
        self.weapons: list[dict[str, object]] = []
        self.target_tile: list[int] = []
        self.row = 0
        unit_object = request["unit_object"]
        if type(unit_object) is not int:
            raise ValueError("unit_object must be an integer")
        self.unit_object: int = unit_object

    def record(self, stage: str, **facts: object) -> None:
        self.stages.append({"stage": stage, "facts": facts})

    def guard(self) -> None:
        """Never start a read or press that the helper's hard deadline would cancel midway."""
        if self.io.time_left() <= GUARD_SECONDS:
            raise _Stop(self.current, "act_deadline")

    async def steady(self, call: Callable[[], Awaitable[Any]], tries: int = READ_RETRIES) -> Any:
        """Reads during animations can fail briefly (emulator not running normally): retry."""
        for attempt in range(tries):
            self.guard()
            try:
                return await call()
            except ActIOError:
                if attempt == tries - 1:
                    raise
                await self.io.sleep(1.0)

    async def tap(self, button: str) -> None:
        self.guard()
        await self.io.press(button, 2)

    async def retreat(self, count: int) -> None:
        for _ in range(count):
            await self.io.press("cross", 2)
            await self.io.sleep(0.6)

    # ---- plan ---------------------------------------------------------------------------
    async def plan(self, *, moved: bool = False) -> dict[str, object]:
        state = await self.io.state()
        self.state0 = state
        units = _units(state)
        unit = _find(units, self.unit_object)
        if unit is None:
            raise _Stop("plan", "unit_not_found")
        if unit.get("raw_menu_group_byte") != ALLY_GROUP or not _alive(unit):
            raise _Stop("plan", "unit_not_ally")
        if self.move_to is None and self.attack is None:
            raise _Stop("plan", "nothing_to_do")
        if not unit.get("counted_as_unmoved"):
            raise _Stop("plan", "unit_already_acted")
        here = _tile(unit)
        if self.move_to is not None:
            if self.move_to == here:
                raise _Stop("plan", "move_to_current_tile")
            if any(_tile(u) == self.move_to for u in units if _alive(u)):
                raise _Stop("plan", "move_tile_occupied")
        facts: dict[str, object] = {"unit": self.unit_object, "tile": here,
                                    "move_to": self.move_to}
        if self.attack is not None:
            weapons = await self.io.read_weapons(self.unit_object)
            rows = weapons.get("weapons")
            if not isinstance(rows, list):
                raise _Stop("plan", "weapons_unreadable")
            self.weapons = [dict(w) for w in rows]
            planned = dict(unit)
            if self.move_to is not None:
                planned["tile_x"], planned["tile_y"] = self.move_to
            others = [u for u in units if u.get("object") != self.unit_object]
            try:
                answer = targets.targets_in_range(planned, [planned, *others], weapons,
                                                  moved=moved or self.move_to is not None)
            except ValueError as exc:
                raise _Stop("plan", "targets_unreadable", {"detail": str(exc)}) from exc
            names = [w.get("name") for w in self.weapons]
            wanted = self.attack.get("weapon")
            if wanted not in names:
                raise _Stop("plan", "unknown_weapon", {"weapons": names})
            self.row = names.index(wanted)
            entry = answer["weapons"][self.row]  # type: ignore[index]
            if not entry["usable"]:
                raise _Stop("plan", "weapon_unusable", {"why": entry["unusable_reason"]})
            hit = [t for t in entry["targets"] if t["object"] == self.attack.get("target_object")]
            if not hit:
                raise _Stop("plan", "target_not_in_range",
                            {"candidates": [t["object"] for t in entry["targets"]]})
            self.target_tile = [int(n) for n in hit[0]["tile"]]
            facts.update(weapon=wanted, row=self.row, target=self.attack.get("target_object"),
                         target_tile=self.target_tile)
        self.record("plan", **facts)
        return unit

    # ---- stages -------------------------------------------------------------------------
    async def select(self, unit: Mapping[str, object]) -> None:
        self.current = "select"
        self.guard()
        walk = await self.io.goto(_tile(unit))
        if not walk.get("reached"):
            raise _Stop("select", "cursor_did_not_reach_tile", {"walk": dict(walk)})
        await self.tap("circle")
        self.depth = 1
        await self.io.sleep(0.8)
        self.record("select", cursor=walk.get("cursor"))

    async def move(self, unit: Mapping[str, object]) -> None:
        self.current = "move"
        self.guard()
        assert self.move_to is not None
        here = _tile(unit)
        await self.tap("circle")
        self.depth = 2
        await self.io.sleep(0.8)
        state = await self.io.state()
        reachable = _reachable(state)
        if not centered(here, reachable):
            raise _Stop("move", "range_not_centered_on_unit", retreat=self.depth)
        if (self.move_to[0], self.move_to[1]) not in {(x, y) for x, y, _ in reachable}:
            raise _Stop("move", "destination_not_reachable", {"tiles": len(reachable)},
                        retreat=self.depth)
        walk = await self.io.goto(self.move_to)
        if not walk.get("reached"):
            raise _Stop("move", "cursor_did_not_reach_tile", {"walk": dict(walk)},
                        retreat=self.depth)
        await self.tap("circle")
        before = _units(self.state0)
        after: list[dict[str, object]] = before
        moved = None
        for _ in range(MOVE_POLLS):
            await self.io.sleep(0.5)
            after = _units(await self.steady(self.io.state))
            moved = _find(after, self.unit_object)
            if moved is not None and _tile(moved) == self.move_to:
                break
        if moved is None or _tile(moved) != self.move_to:
            raise _Stop("move", "move_not_confirmed", {"tile": None if moved is None
                                                       else _tile(moved)})
        self.depth = 0
        old = _find(before, self.unit_object)
        assert old is not None
        if not (isinstance(moved.get("en"), int) and moved["en"] < old["en"]):  # type: ignore[operator]
            raise _Stop("move", "en_not_charged", {"en": [old.get("en"), moved.get("en")]})
        stray = [d for d in _deltas(before, after) if d["object"] != self.unit_object]
        if stray:
            raise _Stop("move", "other_units_changed", {"changes": stray[:4]})
        self.record("move", tile=_tile(moved), en=[old["en"], moved["en"]])

    async def attack_menu(self) -> None:
        self.current = "attack_menu"
        self.guard()
        if self.move_to is None:
            await self.tap("down")             # unmoved unit: Move, Attack, ...
            await self.io.sleep(0.3)
        await self.tap("circle")
        self.depth += 1
        await self.io.sleep(0.8)
        menu = await self.io.menu_row()
        if menu is None or menu[1] != len(self.weapons):
            raise _Stop("attack_menu", "weapon_list_not_open", {"menu": menu})
        self.record("attack_menu", rows=menu[1], row=menu[0])

    async def weapon(self) -> None:
        self.current = "weapon"
        self.guard()
        menu = await self.io.menu_row()
        row = menu[0] if menu else -1
        for _ in range(self.row):
            await self.tap("down")
            await self.io.sleep(0.25)
        for _ in range(8):
            menu = await self.io.menu_row()
            row = menu[0] if menu else -1
            if row == self.row:
                break
            await self.io.sleep(0.25)
        if row != self.row:
            raise _Stop("weapon", "weapon_row_mismatch", {"row": row, "wanted": self.row},
                        retreat=self.depth)
        await self.tap("circle")
        self.depth += 1
        await self.io.sleep(0.8)
        self.record("weapon", row=row, name=self.attack and self.attack.get("weapon"))

    async def target(self) -> None:
        self.current = "target"
        self.guard()
        walk = await self.io.goto(self.target_tile)
        if not walk.get("reached"):
            raise _Stop("target", "cursor_did_not_reach_tile", {"walk": dict(walk)},
                        retreat=self.depth)
        hit = await self.io.hit()
        if hit.get("state") != "hit":
            raise _Stop("target", "target_not_hittable", {"hit": dict(hit)}, retreat=self.depth)
        self.record("target", tile=self.target_tile, hit=hit.get("hit"))

    async def forecast(self) -> dict[str, object]:
        self.current = "forecast"
        self.guard()
        await self.tap("circle")
        self.depth += 1
        await self.io.sleep(1.0)
        hit = await self.io.hit()
        if hit.get("state") != "hit":
            raise _Stop("forecast", "forecast_not_shown", {"hit": dict(hit)}, retreat=self.depth)
        facts: dict[str, object] = {"hit": hit.get("hit"), "tile": self.target_tile}
        self.record("forecast", **facts)
        return facts

    async def fire(self) -> None:
        self.current = "fire"
        self.guard()
        hit = await self.io.hit()
        walk = await self.io.state()
        cursor = walk.get("cursor")
        if (hit.get("state") != "hit" or not isinstance(cursor, Mapping)
                or [cursor.get("x"), cursor.get("y")] != self.target_tile):
            raise _Stop("fire", "not_at_forecast", {"hit": dict(hit), "cursor": cursor})
        self.state0 = walk
        unit = _find(_units(walk), self.unit_object)
        weapons = await self.io.read_weapons(self.unit_object)
        rows = weapons.get("weapons")
        if unit is None or not isinstance(rows, list):
            raise _Stop("fire", "unit_not_readable")
        weapon = rows[self.row]
        await self.tap("start")
        spent = False
        # No memory reads while the battle scene loads: pausing the CPU then wedged the emulator
        # (live trials act1/act2, 20 Oct).
        await self.io.sleep(ANIMATION_SECONDS)
        for _ in range(FIRE_POLLS):
            state = await self.steady(self.io.state)
            now = _find(_units(state), self.unit_object)
            again = await self.steady(lambda: self.io.read_weapons(self.unit_object))
            new = again["weapons"][self.row]
            if (now is not None and isinstance(now.get("en"), int)
                    and now["en"] < unit["en"]) or (  # type: ignore[operator]
                    isinstance(new.get("ammo"), int) and isinstance(weapon.get("ammo"), int)
                    and new["ammo"] < weapon["ammo"]):
                spent = True
                break
            await self.io.sleep(1.5)
        if not spent:
            raise _Stop("fire", "start_not_confirmed")
        self.record("fire", ammo=[weapon.get("ammo"), new.get("ammo")],
                    en=[unit["en"], now["en"] if now else None])

    async def result(self) -> None:
        self.current = "result"
        self.guard()
        await self.io.sleep(2.0)
        presses = 0
        while True:
            unit = _find(_units(await self.steady(self.io.state)), self.unit_object)
            if unit is not None and not unit.get("counted_as_unmoved") and (
                    unit.get("counter_value") == 0):
                break
            if presses >= RESULT_PRESSES:
                raise _Stop("result", "result_not_dismissed", {"presses": presses})
            await self.tap("circle")
            presses += 1
            await self.io.sleep(1.5)
        self.record("result", presses=presses)


def _alive(unit: Mapping[str, object]) -> bool:
    hp = unit.get("hp")
    return isinstance(hp, int) and hp > 0


async def run_act(request: Mapping[str, object], io: ActIO, *, commit: bool = False,
                  phase: str = "run") -> dict[str, object]:
    """Execute one instruction. phase "fire" continues from a shown forecast (Start + result)."""
    run = _Run(request, io)
    try:
        if phase == "fire":
            if run.attack is None:
                raise _Stop("plan", "nothing_to_fire")
            run.move_to = None              # the Move was confirmed by the earlier call
            unit = await run.plan(moved=bool(request.get("move_to")))
            await run.fire()
            await run.result()
        else:
            unit = await run.plan()
            await run.select(unit)
            if run.move_to is not None:
                await run.move(unit)
            if run.attack is None:
                return await _finish(run, "moved", io)
            await run.attack_menu()
            await run.weapon()
            await run.target()
            facts = await run.forecast()
            if not commit or io.time_left() < FIRE_NEEDS:
                return {"ok": True, "phase": "forecast", "stages": run.stages, "forecast": facts,
                        "fire_separately": bool(commit)}
            await run.fire()
            await run.result()
        return await _finish(run, "done", io)
    except ActIOError as exc:
        return {"ok": False, "stage": run.current, "reason": f"io_error: {exc}",
                "facts": {}, "stages": run.stages, "needs_screenshot": True}
    except _Stop as stop:
        if stop.retreat:
            await run.retreat(stop.retreat)
        return {"ok": False, "stage": stop.stage, "reason": stop.reason, "facts": stop.facts,
                "stages": run.stages, "needs_screenshot": stop.stage != "plan"}


async def _finish(run: _Run, phase: str, io: ActIO) -> dict[str, object]:
    after = _units(await run.steady(io.state))
    return {"ok": True, "phase": phase, "stages": run.stages,
            "deltas": _deltas(_units(run.state0), after)}
