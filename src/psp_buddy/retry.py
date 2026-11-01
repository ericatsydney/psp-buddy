"""Checkpoint retries (M12): the attempt ledger, the retry decision and the checkpoint manifest.

Pure logic, no emulator access. One attempt is one turn cycle from a checkpoint saved at the start
of a player phase (M9/M11 turn, M10 End Turn and strict enemy phase). User decisions (25 Oct): a
defeat is any ally destroyed or lost; the game replays deterministically (run m11cp4), so each
retry protects the allies lost so far (they only Standby); at most three retries.
"""

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ALLY_GROUP = 0
LOSSES = ("ally_destroyed", "unit_lost")
MAX_RETRIES = 3


def _units(state: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    units = state.get("units")
    if not isinstance(units, list) or not units:
        raise ValueError("state has no units")
    for u in units:
        if not all(type(u.get(k)) is int for k in ("object", "raw_menu_group_byte", "hp", "en",
                                                    "tile_x", "tile_y")):
            raise ValueError("unit with unreadable fields")
    return units


def _turn(state: Mapping[str, Any]) -> int:
    turn = state.get("turn")
    value = turn.get("turn") if isinstance(turn, Mapping) else None
    if type(value) is not int:
        raise ValueError("turn counter unreadable")
    return value


def _record(u: Mapping[str, Any]) -> dict[str, Any]:
    return {"object": u["object"], "group": u["raw_menu_group_byte"], "hp": u["hp"], "en": u["en"],
            "tile": [u["tile_x"], u["tile_y"]], "unmoved": u.get("counted_as_unmoved") is True}


def snapshot(state: Mapping[str, Any], file_sha256: str) -> dict[str, Any]:
    """What a loaded save state must reproduce, at any point of a turn (M15: a user's slot is
    usually mid-turn); `mismatches` compares against it like a manifest."""
    if not re.fullmatch(r"[0-9a-f]{64}", file_sha256):
        raise ValueError("checkpoint hash must be a SHA-256 hex digest")
    return {"sha256": file_sha256, "turn": _turn(state),
            "units": [_record(u) for u in _units(state)]}


def manifest(state: Mapping[str, Any], file_sha256: str) -> dict[str, Any]:
    """What a checkpoint must reproduce: turn and every unit's HP, EN, tile and unmoved flag."""
    found = snapshot(state, file_sha256)
    allies = [u for u in found["units"] if u["group"] == ALLY_GROUP and u["hp"] > 0]
    if not allies or not all(u["unmoved"] for u in allies):
        raise ValueError("a checkpoint needs the start of a player phase (every ally unmoved)")
    return found


def mismatches(saved: Mapping[str, Any], state: Mapping[str, Any]) -> list[str]:
    """Differences between a checkpoint's manifest and the state after loading it ([] = match)."""
    try:
        turn = _turn(state)
        now = {u["object"]: _record(u) for u in _units(state)}
    except ValueError:
        return ["state unreadable"]
    found = [] if turn == saved["turn"] else [f"turn {saved['turn']} -> {turn}"]
    for want in saved["units"]:
        got = now.get(want["object"])
        if got is None:
            found.append(f"{want['object']} missing")
            continue
        # The unmoved flag is read for the player's own units only (26 Oct: compact foe rows).
        keys = ("hp", "en", "tile", "unmoved", "group") if want["group"] == ALLY_GROUP else (
            "hp", "en", "tile", "group")
        found += [f"{want['object']} {key} {want[key]} -> {got[key]}"
                  for key in keys if got[key] != want[key]]
    return found


def lost_allies(saved: Mapping[str, Any], state: Mapping[str, Any]) -> list[int]:
    """Allies living in the checkpoint that are gone or at 0 HP now (any cause: a counter in the
    player turn vanishes before End Turn, so the enemy-phase report alone misses it)."""
    now = {u["object"]: u for u in _units(state)}
    return [u["object"] for u in saved["units"] if u["group"] == ALLY_GROUP and u["hp"] > 0
            and (u["object"] not in now or now[u["object"]]["hp"] == 0)]


@dataclass
class Attempt:
    number: int
    protected: tuple[int, ...]
    outcome: str | None = None          # done | lost | forced_retry | stopped
    reason: str | None = None
    lost: tuple[int, ...] = ()


class Ledger:
    """Attempts from one checkpoint; `start` then `finish` per attempt."""

    def __init__(self, checkpoint: Mapping[str, Any], *, max_retries: int = MAX_RETRIES) -> None:
        self.checkpoint = dict(checkpoint)
        self.max_retries = max_retries
        self.attempts: list[Attempt] = []
        self.done = False
        self.gave_up: str | None = None

    def _protected(self) -> tuple[int, ...]:
        return tuple(sorted({obj for a in self.attempts for obj in a.lost}))

    def start(self) -> Attempt:
        if self.done or self.gave_up or (self.attempts and self.attempts[-1].outcome is None):
            raise ValueError("no attempt may start now")
        attempt = Attempt(len(self.attempts) + 1, self._protected())
        self.attempts.append(attempt)
        return attempt

    def finish(self, result: Mapping[str, Any], *, lost: Iterable[int] = (),
               forced: bool = False) -> str:
        """Record the attempt's end and say what comes next: done, retry or give_up."""
        if not self.attempts or self.attempts[-1].outcome is not None:
            raise ValueError("finish needs a started attempt")
        attempt = self.attempts[-1]
        attempt.reason = result.get("reason")
        lost = tuple(lost)
        retries_left = len(self.attempts) <= self.max_retries
        if result.get("phase") == "done" and lost and not forced:
            # An ally lost before End Turn (a counter) leaves the enemy phase "done" (25 Oct).
            attempt.reason = "unit_lost"
        elif result.get("phase") == "done" and not forced:
            attempt.outcome, self.done = "done", True
            return "done"
        if forced:
            # Agent-declared reload to prove the retry path when nothing was lost (plan Task 7).
            attempt.outcome = "forced_retry"
            return "retry" if retries_left else self._give_up("retries_used")
        if attempt.reason not in LOSSES:
            attempt.outcome = "stopped"
            return self._give_up(str(attempt.reason))
        attempt.outcome = "lost"
        new = tuple(sorted(set(lost) - set(attempt.protected)))
        attempt.lost = new
        if not new:
            return self._give_up("nothing_new_to_protect")
        return "retry" if retries_left else self._give_up("retries_used")

    def _give_up(self, why: str) -> str:
        self.gave_up = why
        return "give_up"


def report(ledger: Ledger) -> dict[str, Any]:
    """retry-report.json content."""
    return {"checkpoint": ledger.checkpoint, "max_retries": ledger.max_retries,
            "done": ledger.done, "gave_up": ledger.gave_up,
            "attempts": [{"number": a.number, "protected": list(a.protected), "outcome": a.outcome,
                          "reason": a.reason, "lost": list(a.lost)} for a in ledger.attempts]}


def write_report(ledger: Ledger, path: Path) -> str | None:
    """Write retry-report.json; an error is returned, never raised."""
    try:
        path.write_text(json.dumps(report(ledger), allow_nan=False, indent=1), encoding="utf-8")
    except (OSError, TypeError, ValueError) as exc:
        return repr(exc)
    return None
