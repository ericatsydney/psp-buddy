"""Bounded, screenshot-grounded cursor and Info-menu navigation (no battle commands)."""

import hashlib
import io
import json
import os
import re
import stat
import time
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .backup import _safe_path
from .debugger import DebuggerAdapter
from .launch import LaunchSession
from .navigation_mailbox import NavigationRefused

MAX_TAPS = 16
MAX_ACTION_TAPS = 24
MAX_IMAGE_BYTES = 8 * 1024 * 1024
DIRECTIONS = ("up", "down", "left", "right")
CONTEXTS = ("map", "unit_commands", "info", "move_range", "weapon_list", "target_select",
            "attack_forecast")
ACTION_CONTEXTS = ("unit_commands", "move_range", "weapon_list", "target_select",
                   "attack_forecast")
# purpose -> (allowed buttons, allowed screen contexts, extra required key)
PURPOSES: dict[str, tuple[tuple[str, ...], tuple[str, ...], str | None]] = {
    "cursor": (DIRECTIONS, ("map",), None),
    "menu_direction": (DIRECTIONS, ("unit_commands",), None),
    "open_unit_menu": (("circle",), ("map",), "cursor_tile"),
    "open_info": (("circle",), ("unit_commands",), "highlighted_entry"),
    "cancel": (("cross",), ("info",) + ACTION_CONTEXTS, None),
    "open_move": (("circle",), ("unit_commands",), "highlighted_entry"),
    "move_cursor": (DIRECTIONS, ("move_range",), None),
    "confirm_move": (("circle",), ("move_range",), "destination_tile"),
    "open_attack": (("circle",), ("unit_commands",), "highlighted_entry"),
    "select_weapon": (DIRECTIONS + ("circle",), ("weapon_list",), "weapon_name"),
    "select_target": (DIRECTIONS, ("target_select",), None),
    "choose_target": (("circle",), ("target_select",), "target_name"),
    "confirm_attack": (("start",), ("attack_forecast",), "target_name"),
    "standby_after_move": (("circle",), ("unit_commands",), "highlighted_entry"),
}
ACTION_PURPOSES = ("open_move", "move_cursor", "confirm_move", "open_attack", "select_weapon",
                   "select_target", "choose_target", "confirm_attack", "standby_after_move")
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
        if (actions not in (["move"], ["move", "standby"], ["attack"], ["attack_recon"])
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
        if set(value) != wanted:
            raise ValueError("unexpected declaration fields")
        return dict(value)

    def _check_action(self, purpose: str, arguments: Mapping[str, object]) -> None:
        decl = self._declaration
        if decl is None:
            raise ValueError("no action declaration for this trial")
        actions = decl["actions"]
        assert isinstance(actions, list)
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
        if operation not in ("press", "verify", "observe"):
            raise ValueError("unsupported operation")
        keys = set(arguments)
        if arguments.get("sequence") != self._next or type(arguments.get("sequence")) is not int:
            raise ValueError("out-of-order navigation sequence")
        if arguments.get("context") not in CONTEXTS:
            raise ValueError("invalid screen context")
        if operation == "observe":
            if keys != BASE_KEYS or self._observe_stage is None or self._stages >= 40:
                raise ValueError("observe requires a screenshot reference and a stage observer")
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
        if self._uses.get(name, 0) >= (1 if arguments["button"] in ("circle", "start") else 2):
            raise ValueError("screenshot already used; a fresh frame is required")
        return name, purpose

    def _budget(self) -> int:
        return MAX_ACTION_TAPS if self._declaration else MAX_TAPS

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
        self._uses[name] = self._uses.get(name, 0) + 1
        try:
            if operation == "observe":
                assert self._observe_stage is not None
                self._stages += 1
                staged = dict(await self._observe_stage(self._stages))
                self._log({"sequence": sequence, "operation": "observe", "screen": name,
                           "context": arguments["context"], "stage": self._stages})
                return {**staged, "sequence": sequence, "stage": self._stages}
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
        except BaseException:
            self._failed = True
            raise
