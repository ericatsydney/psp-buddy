"""Bounded, screenshot-grounded cursor and Info-menu navigation (no battle commands)."""

import asyncio
import hashlib
import io
import json
import os
import re
import stat
import time
from collections.abc import Awaitable, Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

from . import act as act_macro
from . import battle_state, plan_act, turn
from .backup import _safe_path
from .debugger import DebuggerAdapter
from .launch import LaunchSession
from .navigation_mailbox import NavigationRefused
from .policy import parse_policy
from .weapons import RAM_END, RAM_START

MAX_TAPS = 16
MAX_ACTION_TAPS = 40
MAX_DUMPS = 24
MAX_STATE_READS = 200
MAX_WEAPON_READS = 200
MAX_TARGET_READS = 200
MAX_HIT_READS = 400
MAX_GOTO_PRESSES = 400              # cursor-only presses per trial (separate from the tap budget)
MAX_PROBES = 60
MAX_ACTS = 40
MAX_ACT_PRESSES = 1000              # presses sent by `act` per trial (taps and cursor walks)
ACT_PRESS_RESERVE = 60              # a run starts only with at least this many presses left
ACT_SECONDS = 105                   # cooperative budget; the helper cancels hard at 120 s, which
                                    # would leave the emulator paused, so the macro never gets there
MAX_GOTO_STEPS = 80
MAX_GOTO_JUMP = 40
GOTO_LONG_HOLD = 14                 # frames; a long hold repeats the cursor move unpredictably
GOTO_LONG_FROM = 10**9              # OFF: live test 19 Oct overshot/jumped, taps are reliable
MAX_RESPONSE_BYTES = 15000          # the mailbox limit is 16384 including its envelope
MAX_IMAGE_BYTES = 8 * 1024 * 1024
DIRECTIONS = ("up", "down", "left", "right")
CONTEXTS = ("map", "unit_commands", "info", "move_range", "weapon_list", "target_select",
            "attack_forecast", "result", "system_menu", "enemy_phase")
ACTION_CONTEXTS = ("unit_commands", "move_range", "weapon_list", "target_select",
                   "attack_forecast")
# purpose -> (allowed buttons, allowed screen contexts, extra required key)
PURPOSES: dict[str, tuple[tuple[str, ...], tuple[str, ...], str | None]] = {
    "cursor": (DIRECTIONS, ("map",), None),
    "menu_direction": (DIRECTIONS, ("unit_commands",), None),
    "open_unit_menu": (("circle",), ("map",), "cursor_tile"),
    "open_info": (("circle",), ("unit_commands",), "highlighted_entry"),
    "cancel": (("cross",), ("info", "move_range", "weapon_list", "target_select",
                            "attack_forecast", "system_menu"), None),
    "open_move": (("circle",), ("unit_commands",), "highlighted_entry"),
    "move_cursor": (DIRECTIONS, ("move_range",), None),
    "confirm_move": (("circle",), ("move_range",), "destination_tile"),
    "open_attack": (("circle",), ("unit_commands",), "highlighted_entry"),
    "select_weapon": (DIRECTIONS + ("circle",), ("weapon_list",), "weapon_name"),
    "select_target": (DIRECTIONS, ("target_select",), None),
    "choose_target": (("circle",), ("target_select",), "target_name"),
    "confirm_attack": (("start",), ("attack_forecast",), "target_name"),
    "standby_after_move": (("circle",), ("unit_commands",), "highlighted_entry"),
    "dismiss_result": (("circle",), ("result",), None),
    "open_system_menu": (("circle",), ("map",), "cursor_tile"),
    "system_menu_move": (DIRECTIONS, ("system_menu",), None),
    "end_turn": (("circle",), ("system_menu",), "highlighted_entry"),
    "advance_dialog": (("circle",), ("enemy_phase",), None),
}
ACTION_PURPOSES = ("open_move", "move_cursor", "confirm_move", "open_attack", "select_weapon",
                   "select_target", "choose_target", "confirm_attack", "standby_after_move",
                  "dismiss_result", "open_system_menu", "system_menu_move", "end_turn",
                  "advance_dialog")
SYSTEM_PURPOSES = ("open_system_menu", "system_menu_move", "end_turn", "advance_dialog")
ENTRIES = {"open_info": "Info", "open_move": "Move", "open_attack": "Attack",
           "standby_after_move": "Standby"}
BASE_KEYS = {"sequence", "screen_file", "screen_sha256", "context"}
FILE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\.(?:jpg|jpeg|png)", re.I)


def _integer(value: object, lower: int, upper: int) -> bool:
    return type(value) is int and lower <= value <= upper


class InfoNavigation:
    """One instance per protected launch. Any transport failure is terminal."""

    def __init__(
        self,
        session: LaunchSession,
        adapter: DebuggerAdapter,
        target_tile: tuple[int, int],
        evidence_dir: Path,
        verify_observer: Callable[[], Awaitable[Mapping[str, object]]],
        *,
        declaration: Mapping[str, object] | None = None,
        observe_stage: Callable[[int], Awaitable[Mapping[str, object]]] | None = None,
        dump_ram: Callable[[int], Awaitable[Mapping[str, object]]] | None = None,
        occupied_tiles: Iterable[tuple[int, int]] | None = None,
        read_state: Callable[[int], Awaitable[Mapping[str, object]]] | None = None,
        read_weapons: Callable[[int, int], Awaitable[Mapping[str, object]]] | None = None,
        read_targets: Callable[[int, int, bool], Awaitable[Mapping[str, object]]] | None = None,
        read_hit: Callable[[int], Awaitable[Mapping[str, object]]] | None = None,
        read_cursor: Callable[[], Awaitable[tuple[int, int]]] | None = None,
        read_menu_row: Callable[[], Awaitable[tuple[int, int] | None]] | None = None,
        act_time_scale: float = 1.0,
        map_size: tuple[int, int] | None = None,
        poll_seconds: float = 0.05,
        settle_seconds: float = 0.8,
        ally_tiles: Iterable[tuple[int, int]] | None = None,
    ) -> None:
        session.assert_bound()
        if len(target_tile) != 2 or not all(_integer(n, 0, 1023) for n in target_tile):
            raise ValueError("invalid target tile")
        self._adapter = adapter
        self._target = [int(target_tile[0]), int(target_tile[1])]
        self._root = session.memstick_root / "PSP" / "SCREENSHOT"
        self._evidence = evidence_dir
        self._verify = verify_observer
        self._declaration = self._parse_declaration(declaration)
        self._observe_stage = observe_stage
        self._dump_ram = dump_ram
        self._read_state = read_state
        self._read_weapons = read_weapons
        self._weapon_reads = 0
        self._read_targets = read_targets
        self._target_reads = 0
        self._read_hit = read_hit
        self._hit_reads = 0
        self._read_cursor = read_cursor
        self._read_menu_row = read_menu_row
        self._act_scale = act_time_scale
        self._acts = 0
        self._act_presses = 0
        self._act_deadline = 0.0
        self._act_pending: dict[str, object] | None = None
        self._turn = turn.TurnLog()
        self._turn_state: Mapping[str, object] = {}
        self._map_size = map_size
        self._poll = poll_seconds
        self._goto_presses = 0
        self._settle = settle_seconds
        self._ally_tiles = (None if ally_tiles is None
                            else {(int(x), int(y)) for x, y in ally_tiles})
        self._probes = 0
        self._state_reads = 0
        self._occupied = None if occupied_tiles is None else {
            (int(x), int(y)) for x, y in occupied_tiles}
        self._menu_open = False
        self._advances = 0
        self._dumps = 0
        self._done: set[str] = set()
        self._weapon = False
        self._chosen = False
        self._stages = 0
        self._next = 1
        self._taps = 0
        self._finished = False
        self._failed = False
        # Frames present when the last button was released cannot confirm anything.
        self._stale: set[str] = set()
        self._uses: dict[str, int] = {}

    @staticmethod
    def _tile(value: object) -> bool:
        return (isinstance(value, list) and len(value) == 2
                and all(type(n) is int and 0 <= n <= 1023 for n in value))

    @classmethod
    def _parse_declaration(cls, value: Mapping[str, object] | None) -> dict[str, object] | None:
        if value is None:
            return None
        actions = value.get("actions")
        if (actions not in (["move"], ["move", "standby"], ["move", "attack"], ["attack"],
                           ["attack_recon"], ["system_recon"], ["end_turn"], ["probe"],
                           ["act"])
                or not isinstance(value.get("unit"), str)):
            raise ValueError("invalid action declaration")
        assert isinstance(actions, list)
        wanted = {"unit", "actions"}
        if "move" in actions:
            wanted.add("destination_tile")
            if not cls._tile(value.get("destination_tile")):
                raise ValueError("declaration needs destination_tile")
        if "attack" in actions:
            wanted |= {"weapon_name", "target_name"}
            for key in ("weapon_name", "target_name"):
                item = value.get(key)
                if not isinstance(item, str) or not item or len(item) > 64:
                    raise ValueError("declaration needs weapon_name and target_name")
        if "end_turn" in actions:
            wanted.add("entry_label")
            label = value.get("entry_label")
            if not isinstance(label, str) or not label or len(label) > 64:
                raise ValueError("declaration needs entry_label")
        if set(value) != wanted:
            raise ValueError("unexpected declaration fields")
        return dict(value)

    def _check_system(self, purpose: str, arguments: Mapping[str, object],
                      actions: list[object]) -> None:
        recon, ending = "system_recon" in actions, "end_turn" in actions
        if not (recon or ending):
            raise ValueError("system-menu steps are not declared for this trial")
        if purpose == "open_system_menu":
            tile = arguments["cursor_tile"]
            if not self._tile(tile) or self._occupied is None:
                raise ValueError("system menu needs a known empty tile")
            assert isinstance(tile, list)
            if (int(tile[0]), int(tile[1])) in self._occupied:
                raise ValueError("system menu needs a known empty tile")
        elif purpose == "system_menu_move":
            if not self._menu_open:
                raise ValueError("system menu is not open")
        elif purpose == "end_turn":
            decl = self._declaration
            assert decl is not None
            if (not ending or not self._menu_open or "end_turn" in self._done
                    or arguments["highlighted_entry"] != decl["entry_label"]):
                raise ValueError("End Turn is not permitted here")
        elif purpose == "advance_dialog":
            if not ending or "end_turn" not in self._done or self._advances >= 30:
                raise ValueError("nothing to advance")

    def _check_action(self, purpose: str, arguments: Mapping[str, object]) -> None:
        decl = self._declaration
        if decl is None:
            raise ValueError("no action declaration for this trial")
        actions = decl["actions"]
        assert isinstance(actions, list)
        if purpose in SYSTEM_PURPOSES:
            self._check_system(purpose, arguments, actions)
            return
        if ("system_recon" in actions or "end_turn" in actions or "probe" in actions
                or "act" in actions):
            raise ValueError("this trial permits only its declared special steps")
        if purpose == "dismiss_result":
            # Decision-free "Get Result" box; only exists after a declared attack.
            if "attack" not in self._done:
                raise ValueError("no declared attack has been confirmed")
            return
        if purpose == "standby_after_move":
            if "standby" not in actions or "move" not in self._done or "standby" in self._done:
                raise ValueError("Standby is not permitted at this point")
            return
        if "attack_recon" in actions:
            # View-only: open Attack, browse weapons/targets. Never confirm anything.
            if purpose not in ("open_attack", "select_weapon", "select_target"):
                raise ValueError("only viewing is permitted in an Attack recon trial")
            return
        kind = "attack" if purpose in ("open_attack", "select_weapon", "select_target",
                                       "choose_target", "confirm_attack") else "move"
        if kind not in actions:
            raise ValueError("action not declared for this trial")
        if kind == "attack" and "move" in actions and "move" not in self._done:
            raise ValueError("the declared move must be confirmed before attacking")
        if purpose == "confirm_move":
            tile = arguments["destination_tile"]
            if not self._tile(tile) or tile != decl["destination_tile"] or "move" in self._done:
                raise ValueError("move confirm does not match declaration")
        elif purpose == "select_weapon" and arguments["button"] == "circle":
            if arguments["weapon_name"] != decl["weapon_name"]:
                raise ValueError("weapon does not match declaration")
        elif purpose == "choose_target":
            if arguments["target_name"] != decl["target_name"] or not self._weapon:
                raise ValueError("target does not match declaration or no weapon selected")
        elif purpose == "confirm_attack":
            if (arguments["target_name"] != decl["target_name"] or not self._chosen
                    or "attack" in self._done):
                raise ValueError("attack confirm does not match declaration")

    def _frame(self, arguments: Mapping[str, object]) -> str:
        name, digest = arguments["screen_file"], arguments["screen_sha256"]
        if (not isinstance(name, str) or not FILE_NAME.fullmatch(name)
                or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
            raise ValueError("invalid screenshot reference")
        path = self._root / name
        _safe_path(path)
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_IMAGE_BYTES:
            raise ValueError("unsafe or oversized screenshot")
        with path.open("rb") as stream:
            data = stream.read(MAX_IMAGE_BYTES + 1)
            if os.fstat(stream.fileno()).st_ino != info.st_ino:
                raise ValueError("screenshot changed")
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("screenshot hash mismatch")
        try:
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in ("JPEG", "PNG"):
                    raise ValueError("unsupported screenshot format")
                image.load()
                extrema = [band.getextrema() for band in image.convert("RGB").split()]
        except (UnidentifiedImageError, OSError) as exc:
            raise ValueError("undecodable screenshot") from exc
        if all(pair[0] == pair[1] for pair in extrema):
            raise ValueError("blank screenshot")
        return name

    def _check(self, operation: str, arguments: object) -> tuple[str, str | None]:
        if self._finished or self._failed:
            raise ValueError("navigation is terminal; start a fresh protected session")
        if not isinstance(arguments, dict):
            raise ValueError("arguments must be an object")
        if operation not in ("press", "verify", "observe", "dump", "state", "weapons", "targets",
                             "hit", "goto", "probe_move", "act", "plan_act", "turn_next"):
            raise ValueError("unsupported operation")
        keys = set(arguments)
        if arguments.get("sequence") != self._next or type(arguments.get("sequence")) is not int:
            raise ValueError("out-of-order navigation sequence")
        if operation == "state":
            # Pure memory read: no screenshot reference, no input.
            if keys != {"sequence"} or self._read_state is None or (
                    self._state_reads >= MAX_STATE_READS):
                raise ValueError("state read needs only a sequence, a reader and budget")
            return "", None
        if operation == "weapons":
            # Pure memory read of one unit's weapons: no screenshot reference, no input.
            unit_object = arguments.get("object")
            if (keys != {"sequence", "object"} or type(unit_object) is not int
                    or not RAM_START <= unit_object < RAM_END or self._read_weapons is None
                    or self._weapon_reads >= MAX_WEAPON_READS):
                raise ValueError("weapon read needs a sequence, a unit object, a reader and budget")
            return "", None
        if operation == "turn_next":
            # Pure memory read: next ready ally of this turn (bookkeeping in memory only).
            if keys != {"sequence"} or self._read_state is None or (
                    self._state_reads >= MAX_STATE_READS):
                raise ValueError("turn_next needs only a sequence, a reader and budget")
            return "", None
        if operation == "hit":
            # Pure memory read of the hover hit chance (valid only in target select).
            if keys != {"sequence"} or self._read_hit is None or self._hit_reads >= MAX_HIT_READS:
                raise ValueError("hit read needs only a sequence, a reader and budget")
            return "", None
        if operation == "targets":
            # Pure memory read: enemies in range per weapon. No screenshot, no input.
            unit_object = arguments.get("object")
            if (not keys <= {"sequence", "object", "moved"} or not {"sequence", "object"} <= keys
                    or type(unit_object) is not int or not RAM_START <= unit_object < RAM_END
                    or type(arguments.get("moved", False)) is not bool
                    or self._read_targets is None or self._target_reads >= MAX_TARGET_READS):
                raise ValueError("target read needs a sequence, a unit object, a reader and budget")
            return "", None
        if arguments.get("context") not in CONTEXTS:
            raise ValueError("invalid screen context")
        if operation == "observe":
            if keys != BASE_KEYS or self._observe_stage is None or self._stages >= 40:
                raise ValueError("observe requires a screenshot reference and a stage observer")
            return self._frame(arguments), None
        if operation == "goto":
            return self._check_goto(arguments, keys), None
        if operation == "act":
            return self._check_act(arguments, keys), None
        if operation == "plan_act":
            return self._check_plan_act(arguments, keys), None
        if operation == "probe_move":
            return self._check_probe(arguments, keys), None
        if operation == "dump":
            if keys != BASE_KEYS or self._dump_ram is None or self._dumps >= MAX_DUMPS:
                raise ValueError("dump requires a screenshot reference, a reader and budget")
            return self._frame(arguments), None
        if operation == "verify":
            if keys != BASE_KEYS or arguments["context"] != "info":
                raise ValueError("verify requires exactly an Info screen reference")
            return self._frame(arguments), None
        if self._taps >= self._budget():
            raise ValueError("navigation input budget exhausted")
        purpose = arguments.get("purpose")
        if not isinstance(purpose, str) or purpose not in PURPOSES:
            raise ValueError("unsupported navigation purpose")
        buttons, contexts, extra = PURPOSES[purpose]
        if purpose == "select_weapon" and arguments.get("button") != "circle":
            extra = None
        if keys != BASE_KEYS | {"button", "duration", "purpose"} | ({extra} if extra else set()):
            raise ValueError("unexpected or missing navigation arguments")
        if arguments["button"] not in buttons or arguments["context"] not in contexts:
            raise ValueError("button or screen context not allowed for this purpose")
        if not _integer(arguments["duration"], 1, 3):
            raise ValueError("duration must be 1..3 frames")
        if purpose in ACTION_PURPOSES:
            self._check_action(purpose, arguments)
        tile = arguments.get("cursor_tile")
        if purpose == "open_unit_menu" and not (self._tile(tile) and tile == self._target):
            raise ValueError("cursor is not on the trusted Destiny tile")
        if purpose in ENTRIES and arguments["highlighted_entry"] != ENTRIES[purpose]:
            raise ValueError("the matching command entry must be visibly highlighted")
        name = self._frame(arguments)
        if arguments["button"] in ("circle", "start") and name in self._stale:
            raise ValueError("a confirming input requires a fresh screenshot")
        if self._uses.get(name, 0) >= (1 if arguments["button"] in ("circle", "start") else 4):
            raise ValueError("screenshot already used; a fresh frame is required")
        return name, purpose

    def _budget(self) -> int:
        return MAX_ACTION_TAPS if self._declaration else MAX_TAPS

    def _check_probe(self, arguments: Mapping[str, object], keys: set[str]) -> str:
        decl = self._declaration
        if (decl is None or decl["actions"] != ["probe"] or keys != BASE_KEYS | {"tile"}
                or self._read_cursor is None or self._read_state is None
                or self._map_size is None or self._ally_tiles is None
                or arguments["context"] != "map" or self._probes >= MAX_PROBES):
            raise ValueError("probe_move needs the probe declaration, readers and a map screenshot")
        tile = arguments["tile"]
        if not (self._tile(tile) and isinstance(tile, list)
                and (tile[0], tile[1]) in self._ally_tiles):
            raise ValueError("probe_move tile must be a living ally of the baseline")
        return self._frame(arguments)

    async def _probe_move(self, tile: list[int]) -> dict[str, object]:
        """Walk to an ally, open its Move range, read costs from memory, back out (view only)."""
        assert self._read_state is not None
        walk = await self._goto(tile)
        if not walk["reached"]:
            return {"ok": False, "reason": "walk_did_not_reach_the_unit", "tile": tile,
                    "walk": walk}
        reachable: list[list[int]] = []
        ok, reason = False, "range_not_centered_on_unit"
        try:
            for _ in range(2):          # circle opens the command menu, circle again picks Move
                await self._adapter.press("circle", 2)
                await asyncio.sleep(self._settle)
            state = dict(await self._read_state(0))
            raw: list[list[int]] = list(state.get("reachable") or [])  # type: ignore[call-overload]
            grid = state.get("map")
            if not raw and isinstance(grid, dict):
                derived = battle_state.reachable_tiles({"cost_rows": grid["cost_rows"]})
                raw = [[t["x"], t["y"], t["cost"]] for t in derived]
            reachable = [[int(x), int(y), int(c)] for x, y, c in raw]
            ok = self._centered(tile, reachable)
        finally:
            for _ in range(2):          # leave Move, then the command menu (nothing was confirmed)
                await self._adapter.press("cross", 2)
                await asyncio.sleep(self._settle)
        return {"ok": ok, "reason": None if ok else reason, "tile": tile,
                "reachable": reachable if ok else [], "walk": walk}

    @staticmethod
    def _centered(tile: list[int], reachable: list[list[int]]) -> bool:
        """A fresh range is centred on the unit; stale costs from another unit fail this test."""
        return act_macro.centered(tile, reachable)

    def _check_act(self, arguments: Mapping[str, object], keys: set[str]) -> str:
        decl = self._declaration
        optional = {"move_to", "attack", "commit", "phase"}
        required = BASE_KEYS | {"unit_object"}
        if (decl is None or decl["actions"] != ["act"] or not required <= keys
                or not keys <= required | optional
                or self._read_state is None or self._read_weapons is None
                or self._read_hit is None or self._read_cursor is None
                or self._read_menu_row is None or self._map_size is None):
            raise ValueError("act needs the act declaration, all memory readers and a request")
        phase = arguments.get("phase", "run")
        if phase not in ("run", "fire"):
            raise ValueError("act phase must be run or fire")
        if arguments["context"] != ("attack_forecast" if phase == "fire" else "map"):
            raise ValueError("act needs a map screenshot (an attack-forecast one for fire)")
        unit_object = arguments["unit_object"]
        if type(unit_object) is not int or not RAM_START <= unit_object < RAM_END:
            raise ValueError("act needs a unit object")
        move_to = arguments.get("move_to")
        if move_to is not None and not self._tile(move_to):
            raise ValueError("move_to must be [x, y]")
        attack = arguments.get("attack")
        if attack is not None:
            weapon = attack.get("weapon") if isinstance(attack, dict) else None
            victim = attack.get("target_object") if isinstance(attack, dict) else None
            slot = attack.get("slot") if isinstance(attack, dict) else None
            if (not isinstance(attack, dict)
                    or not {"weapon", "target_object"} <= set(attack) <= {"weapon", "target_object",
                                                                           "slot"}
                    or not isinstance(weapon, str) or not 0 < len(weapon) <= 64
                    or type(victim) is not int or not RAM_START <= victim < RAM_END
                    or ("slot" in attack and (type(slot) is not int or not 0 <= slot < 21))):
                raise ValueError("attack needs a weapon name, an optional slot and a target object")
        if move_to is None and attack is None:
            raise ValueError("act needs a move_to or an attack")
        if type(arguments.get("commit", False)) is not bool:
            raise ValueError("commit must be a boolean")
        if phase == "fire":
            if attack is None or self._act_pending != self._act_key(arguments):
                raise ValueError("no matching forecast is waiting to be fired")
        elif self._act_pending is not None:
            raise ValueError("a forecast is waiting: fire it or cancel it first")
        if self._acts >= MAX_ACTS or self._act_presses + ACT_PRESS_RESERVE > MAX_ACT_PRESSES:
            raise ValueError("act budget for this trial is exhausted")
        name = self._frame(arguments)
        if name in self._stale or self._uses.get(name, 0) >= 1:
            raise ValueError("act needs a fresh screenshot")
        return name

    def _check_plan_act(self, arguments: Mapping[str, object], keys: set[str]) -> str:
        decl = self._declaration
        required = BASE_KEYS | {"unit_object", "policy"}
        if (decl is None or decl["actions"] != ["act"] or not required <= keys
                or not keys <= required | {"bosses", "min_hit"}
                or self._read_state is None or self._read_weapons is None
                or self._read_hit is None or self._read_cursor is None
                or self._read_menu_row is None or self._map_size is None):
            raise ValueError("plan_act needs the act declaration, all memory readers and a request")
        if arguments["context"] != "map":
            raise ValueError("plan_act needs a map screenshot")
        unit_object, text = arguments["unit_object"], arguments["policy"]
        bosses = arguments.get("bosses", [])
        if (type(unit_object) is not int or not RAM_START <= unit_object < RAM_END
                or not isinstance(text, str) or len(text) > 400
                or not isinstance(bosses, list) or len(bosses) > 8
                or not all(type(b) is int and RAM_START <= b < RAM_END for b in bosses)):
            raise ValueError("plan_act needs a unit, a policy text and optional bosses")
        min_hit = arguments.get("min_hit", plan_act.MIN_HIT)
        if type(min_hit) is not int or not 1 <= min_hit <= 100:
            raise ValueError("min_hit must be a whole number from 1 to 100")
        parse_policy(text)          # an unsupported clause is refused before any input
        if self._act_pending is not None:
            raise ValueError("a forecast is waiting: fire it or cancel it first")
        if self._acts >= MAX_ACTS or self._act_presses + ACT_PRESS_RESERVE > MAX_ACT_PRESSES:
            raise ValueError("act budget for this trial is exhausted")
        name = self._frame(arguments)
        if name in self._stale or self._uses.get(name, 0) >= 1:
            raise ValueError("plan_act needs a fresh screenshot")
        return name

    async def _run_plan_act(self, arguments: Mapping[str, object]) -> dict[str, object]:
        self._acts += 1
        self._act_deadline = time.monotonic() + ACT_SECONDS
        unit_object, text = arguments["unit_object"], arguments["policy"]
        assert type(unit_object) is int and isinstance(text, str)
        bosses = arguments.get("bosses", [])
        assert isinstance(bosses, list)
        outcome: dict[str, object] = await plan_act.plan_and_act(
            self._act_io(), parse_policy(text), unit_object, bosses=frozenset(bosses),
            min_hit=int(arguments.get("min_hit", plan_act.MIN_HIT)),  # type: ignore[call-overload]
            damage_log=self._evidence / "damage-log.jsonl")
        self._act_pending = None
        self._stale = {p.name for p in self._root.iterdir()} if self._root.is_dir() else set()
        self._turn.record(unit_object, outcome)
        error = self._write_turn_report()
        return {**outcome, "report_error": error} if error else outcome

    def _write_turn_report(self) -> str | None:
        """Rewrite turn-report.json; a write error is returned, never raised (the action may
        already have happened, and an exception would disable the helper mid-turn)."""
        try:
            self._evidence.mkdir(parents=True, exist_ok=True)
            data = turn.report(self._turn, self._turn_state)
            (self._evidence / "turn-report.json").write_text(
                json.dumps(data, allow_nan=False, indent=1), encoding="utf-8")
        except (OSError, TypeError, ValueError) as exc:
            return repr(exc)
        return None

    @staticmethod
    def _act_key(arguments: Mapping[str, object]) -> dict[str, object]:
        return {"unit_object": arguments["unit_object"], "move_to": arguments.get("move_to"),
                "attack": arguments.get("attack")}

    def _act_io(self) -> act_macro.ActIO:
        nav = self

        class Io:
            async def press(self, button: str, frames: int = 2) -> None:
                if nav._act_presses >= MAX_ACT_PRESSES:
                    raise act_macro.ActIOError("act press budget exhausted")
                nav._act_presses += 1
                nav._log({"operation": "act_press", "button": button,
                          "monotonic_ns": time.monotonic_ns()})
                await nav._adapter.press(button, frames)

            async def goto(self, tile: list[int]) -> Mapping[str, object]:
                assert nav._read_cursor is not None
                try:
                    return await nav._goto(tile)
                except NavigationRefused as exc:
                    return {"reached": False, "reason": str(exc)}

            async def state(self) -> Mapping[str, object]:
                assert nav._read_state is not None
                nav._state_reads += 1
                result: Mapping[str, object] = await nav._act_read(
                    nav._read_state(nav._state_reads))
                return result

            async def read_weapons(self, unit_object: int) -> Mapping[str, object]:
                assert nav._read_weapons is not None
                nav._weapon_reads += 1
                result: Mapping[str, object] = await nav._act_read(
                    nav._read_weapons(nav._weapon_reads, unit_object))
                return result

            async def hit(self) -> Mapping[str, object]:
                assert nav._read_hit is not None
                nav._hit_reads += 1
                result: Mapping[str, object] = await nav._act_read(nav._read_hit(nav._hit_reads))
                return result

            async def menu_row(self) -> tuple[int, int] | None:
                assert nav._read_menu_row is not None
                result: tuple[int, int] | None = await nav._act_read(nav._read_menu_row())
                return result

            async def sleep(self, seconds: float) -> None:
                await asyncio.sleep(seconds * nav._act_scale)

            def time_left(self) -> float:
                if nav._act_scale == 0:
                    return float("inf")
                return nav._act_deadline - time.monotonic()
        return Io()

    async def _act_read(self, call: Awaitable[Any]) -> Any:
        started = time.monotonic()
        outcome = "ok"
        try:
            return await call
        except (NavigationRefused, ValueError) as exc:
            outcome = f"refused: {exc}"
            raise act_macro.ActIOError(str(exc)) from exc
        finally:
            self._log({"operation": "act_read", "seconds": round(time.monotonic() - started, 2),
                       "outcome": outcome, "monotonic_ns": time.monotonic_ns()})

    async def _run_act(self, arguments: Mapping[str, object]) -> dict[str, object]:
        phase = str(arguments.get("phase", "run"))
        key = self._act_key(arguments)
        self._acts += 1
        self._act_deadline = time.monotonic() + ACT_SECONDS
        outcome = await act_macro.run_act(
            {k: v for k, v in key.items() if v is not None}, self._act_io(),
            commit=bool(arguments.get("commit", False)), phase=phase)
        self._act_pending = (key if outcome.get("ok") and outcome.get("phase") == "forecast"
                             else None)
        # The folder may not exist yet; that must not fail an action that already happened.
        self._stale = {p.name for p in self._root.iterdir()} if self._root.is_dir() else set()
        return outcome

    def _check_goto(self, arguments: Mapping[str, object], keys: set[str]) -> str:
        if (keys != BASE_KEYS | {"target"} or self._read_cursor is None
                or self._map_size is None or arguments["context"] != "map"):
            raise ValueError("goto needs a map-context screenshot, a target and a cursor reader")
        target = arguments["target"]
        width, height = self._map_size
        if not (isinstance(target, list) and len(target) == 2
                and all(type(n) is int for n in target)
                and 0 <= target[0] < width and 0 <= target[1] < height):
            raise ValueError("goto target is outside the map")
        return self._frame(arguments)

    async def _goto(self, target: list[int]) -> dict[str, object]:
        """Walk the map cursor to the target, verifying every step from the cursor field."""
        assert self._read_cursor is not None
        x, y = await self._read_cursor()
        needed = abs(target[0] - x) + abs(target[1] - y)
        if self._goto_presses + needed > MAX_GOTO_PRESSES:
            raise NavigationRefused("cursor press budget for this trial is exhausted")
        presses, stalls, unexpected = 0, 0, False
        while (x, y) != (target[0], target[1]) and presses < MAX_GOTO_STEPS:
            if x != target[0]:
                button, delta, remaining = (("right", (1, 0), target[0] - x) if target[0] > x
                                            else ("left", (-1, 0), x - target[0]))
            else:
                button, delta, remaining = (("down", (0, 1), target[1] - y) if target[1] > y
                                            else ("up", (0, -1), y - target[1]))
            # Long holds repeat the cursor move, so use them for long distances; the loop below
            # re-reads the cursor and corrects any overshoot.
            await self._adapter.press(button, GOTO_LONG_HOLD if remaining >= GOTO_LONG_FROM else 2)
            presses += 1
            self._goto_presses += 1
            moved = (x, y)
            for _ in range(12):
                moved = await self._read_cursor()
                if moved != (x, y):
                    break
                await asyncio.sleep(self._poll)
            if moved == (x, y):
                stalls += 1
                if stalls >= 2:
                    break
                continue
            stalls = 0
            steps = (moved[0] - x) * delta[0] + (moved[1] - y) * delta[1]    # along the move
            sideways = (moved[0] - x) * delta[1] + (moved[1] - y) * delta[0]
            x_old, y_old = x, y
            x, y = moved
            if steps < 1 or sideways != 0 or abs(x - x_old) + abs(y - y_old) > MAX_GOTO_JUMP:
                unexpected = True
                break
        reached = (x, y) == (target[0], target[1])
        return {"reached": reached, "cursor": {"x": x, "y": y}, "presses": presses,
                "stalled": stalls >= 2, "unexpected_move": unexpected,
                "goto_presses_used": self._goto_presses}

    def _log(self, record: dict[str, object]) -> None:
        self._evidence.mkdir(parents=True, exist_ok=True)
        with (self._evidence / "agent-navigation-inputs.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, allow_nan=False) + "\n")

    async def execute(self, operation: str, arguments: object) -> dict[str, object]:
        try:
            name, purpose = self._check(operation, arguments)
        except ValueError as exc:
            raise NavigationRefused(str(exc)) from exc
        assert isinstance(arguments, dict)
        sequence = self._next
        self._next += 1
        if name:
            self._uses[name] = self._uses.get(name, 0) + 1
        try:
            if operation == "probe_move":
                probe_tile = arguments["tile"]
                assert isinstance(probe_tile, list)
                self._probes += 1
                probed = await self._probe_move([int(probe_tile[0]), int(probe_tile[1])])
                self._log({"sequence": sequence, "operation": "probe_move", "screen": name,
                           "tile": probe_tile, "ok": probed["ok"], "reason": probed["reason"]})
                return {**probed, "sequence": sequence}
            if operation == "goto":
                arguments_target = arguments["target"]
                assert isinstance(arguments_target, list)
                outcome = await self._goto([int(arguments_target[0]), int(arguments_target[1])])
                self._log({"sequence": sequence, "operation": "goto", "screen": name,
                           "target": arguments_target, **outcome})
                return {**outcome, "sequence": sequence}
            if operation == "act":
                outcome = await self._run_act(arguments)
                answer = {**outcome, "sequence": sequence, "acts_used": self._acts,
                          "act_presses_used": self._act_presses}
                if len(json.dumps(answer, allow_nan=False)) > MAX_RESPONSE_BYTES:
                    answer = {**answer, "stages": [], "deltas": [], "truncated": True}
                self._log({"sequence": sequence, "operation": "act", "screen": name,
                           "ok": answer.get("ok"), "phase": answer.get("phase"),
                           "stage": answer.get("stage"), "reason": answer.get("reason"),
                           "unit_object": arguments["unit_object"]})
                return answer
            if operation == "plan_act":
                self._evidence.mkdir(parents=True, exist_ok=True)
                outcome = await self._run_plan_act(arguments)
                answer = {**outcome, "sequence": sequence, "acts_used": self._acts,
                          "act_presses_used": self._act_presses}
                if len(json.dumps(answer, allow_nan=False)) > MAX_RESPONSE_BYTES:
                    answer = {**answer, "outcome": {"truncated": True}, "truncated": True}
                self._log({"sequence": sequence, "operation": "plan_act", "screen": name,
                           "ok": answer.get("ok"), "phase": answer.get("phase"),
                           "reason": answer.get("reason"), "unit_object": arguments["unit_object"]})
                return answer
            if operation == "hit":
                assert self._read_hit is not None
                self._hit_reads += 1
                try:
                    hit = dict(await self._read_hit(self._hit_reads))
                except NavigationRefused:
                    # Memory reads are harmless: a refusal consumes neither sequence nor budget.
                    self._next -= 1
                    self._hit_reads -= 1
                    raise
                self._log({"sequence": sequence, "operation": "hit", "hit_read": self._hit_reads})
                return {**hit, "sequence": sequence, "hit_read": self._hit_reads}
            if operation == "targets":
                assert self._read_targets is not None
                target_object = arguments["object"]
                assert isinstance(target_object, int)
                self._target_reads += 1
                try:
                    targets = dict(await self._read_targets(
                        self._target_reads, target_object, bool(arguments.get("moved", False))))
                    answer = {**targets, "sequence": sequence, "target_read": self._target_reads}
                    if len(json.dumps(answer, allow_nan=False)) > MAX_RESPONSE_BYTES:
                        raise NavigationRefused("target list is too large for the mailbox")
                except NavigationRefused:
                    # Memory reads are harmless: a refusal consumes neither sequence nor budget.
                    self._next -= 1
                    self._target_reads -= 1
                    raise
                self._log({"sequence": sequence, "operation": "targets",
                           "object": target_object, "target_read": self._target_reads})
                return answer
            if operation == "weapons":
                assert self._read_weapons is not None
                unit_object = arguments["object"]
                assert isinstance(unit_object, int)
                self._weapon_reads += 1
                try:
                    try:
                        weapons = dict(await self._read_weapons(self._weapon_reads, unit_object))
                    except NavigationRefused:
                        raise
                    except ValueError as exc:
                        # Implausible pointers or records: refuse the read, keep the session.
                        raise NavigationRefused(f"weapons not readable now: {exc}") from exc
                    answer = {**weapons, "sequence": sequence, "weapon_read": self._weapon_reads}
                    if len(json.dumps(answer, allow_nan=False)) > MAX_RESPONSE_BYTES:
                        raise NavigationRefused("weapon list is too large for the mailbox")
                except NavigationRefused:
                    # Memory reads are harmless: a refusal consumes neither sequence nor budget.
                    self._next -= 1
                    self._weapon_reads -= 1
                    raise
                self._log({"sequence": sequence, "operation": "weapons",
                           "object": arguments["object"], "weapon_read": self._weapon_reads})
                return answer
            if operation == "state":
                assert self._read_state is not None
                self._state_reads += 1
                try:
                    state = dict(await self._read_state(self._state_reads))
                    answer = {**state, "sequence": sequence, "state_read": self._state_reads}
                    if len(json.dumps(answer, allow_nan=False)) > MAX_RESPONSE_BYTES:
                        raise NavigationRefused("state is too large for the mailbox")
                except NavigationRefused:
                    # Memory reads are harmless: a refusal consumes neither sequence nor budget.
                    self._next -= 1
                    self._state_reads -= 1
                    raise
                self._log({"sequence": sequence, "operation": "state",
                           "state_read": self._state_reads})
                return answer
            if operation == "turn_next":
                assert self._read_state is not None
                self._state_reads += 1
                try:
                    state = dict(await self._read_state(self._state_reads))
                except NavigationRefused:
                    self._next -= 1
                    self._state_reads -= 1
                    raise
                self._turn_state = state
                chosen = turn.next_unit(state, self._turn)
                answer = {**chosen, "skipped": {str(k): v for k, v in chosen["skipped"].items()},
                          "sequence": sequence}
                error = self._write_turn_report()
                if error:
                    answer["report_error"] = error
                self._log({"sequence": sequence, "operation": "turn_next",
                           "unit_object": answer["unit_object"], "done": answer["done"],
                           "stopped": answer["stopped"]})
                return answer
            if operation == "observe":
                assert self._observe_stage is not None
                self._stages += 1
                staged = dict(await self._observe_stage(self._stages))
                self._log({"sequence": sequence, "operation": "observe", "screen": name,
                           "context": arguments["context"], "stage": self._stages})
                return {**staged, "sequence": sequence, "stage": self._stages}
            if operation == "dump":
                assert self._dump_ram is not None
                self._dumps += 1
                dumped = dict(await self._dump_ram(self._dumps))
                self._log({"sequence": sequence, "operation": "dump", "screen": name,
                           "context": arguments["context"], "dump": self._dumps})
                return {**dumped, "sequence": sequence, "dump": self._dumps}
            if operation == "verify":
                observed = dict(await self._verify())
                self._finished = True
                self._log({"sequence": sequence, "operation": "verify", "screen": name})
                return {**observed, "sequence": sequence}
            self._taps += 1
            receipt = await self._adapter.press(
                str(arguments["button"]), int(arguments["duration"]))
            self._stale = {p.name for p in self._root.iterdir()}
            if purpose == "confirm_move":
                self._done.add("move")
            elif purpose == "standby_after_move":
                self._done.add("standby")
            elif purpose == "open_system_menu":
                self._menu_open = True
            elif purpose == "end_turn":
                self._done.add("end_turn")
                self._menu_open = False
            elif purpose == "advance_dialog":
                self._advances += 1
            elif purpose == "cancel" and arguments["context"] == "attack_forecast":
                self._act_pending = None
            elif purpose == "cancel" and arguments["context"] == "system_menu":
                self._menu_open = False
            elif purpose == "choose_target":
                self._chosen = True
            elif purpose == "confirm_attack":
                self._done.add("attack")
            elif purpose == "select_weapon" and arguments["button"] == "circle":
                self._weapon = True
            self._log({"sequence": sequence, "operation": "press", "purpose": purpose,
                       "button": arguments["button"], "duration": arguments["duration"],
                       "screen": name, "context": arguments["context"],
                       "monotonic_ns": time.monotonic_ns()})
            return {"sequence": sequence, "button": arguments["button"],
                    "duration": arguments["duration"], "purpose": purpose,
                    "receipt": bool(receipt), "taps_remaining": self._budget() - self._taps}
        except NavigationRefused:
            raise            # refused before anything was sent; the session stays usable
        except BaseException:
            self._failed = True
            raise
