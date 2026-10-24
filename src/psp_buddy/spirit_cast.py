"""Cast Sense, else Focus, before a planned attack (M11; user rule 23 Oct).

Live on 23/24 Oct (docs/research/2026-10-23-spirit-recon.md): Circle on the unit opens the Command
menu Move / Attack / Spirit / Info, Down x2 and Circle open the pilot's spirit list on row 0, Down x
row and one Circle cast with no Yes/No, and about a second later the game is back on the map with
the unit unmoved. The Command menu differs per unit (24 Oct, m11menu1 screenshots: Z Gundam has
Move / Attack / Morph / Spirit / Info, and Circle on Morph transforms at once), so its entry count
and cursor row (u32 pair at 0x08E4BE34, found in that recon; stale once the menu closes) must show
a known layout and then the Spirit row before the Circle. No field is known for the spirit list
(the list-cursor candidates failed on a fresh launch, 24 Oct), so the cast counts only afterwards:
the pilot's SP fell by exactly the cost, and the effect mask (pilot runtime +0x14) gained the
spirit's bits. Nothing spent closes the list with Cross and the attack goes on without a Spirit
(status "skipped"); an SP drop other than the cost means something else was cast (a wrong row)
and the act stops ("mismatch"). The candidate bytes are kept in `list_bytes`. Never raises.

Every path that opened a menu ends by proving the map from memory (`on_map`): the cursor must walk
to a neighbouring tile and back, which it cannot do while a menu is open. Two Crosses may leave a
menu open (24 Oct live, m11live2: a unit whose Spirit opened another screen first stayed on the
Command menu and locked the cursor for the rest of the turn), so up to two more Crosses follow;
a menu that still does not close makes the caller stop the turn.
"""

import struct
from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from . import act
from .spirits import EFFECT_BITS, choose_spirit

SPIRIT_NEEDS = 20.0      # seconds the presses, pauses and SP reads take (budget, spec)
MAX_ROW = 3              # at most 6 presses: Circle, Down x2, Circle, Down x row, Circle ...
MENU_PAUSE = 0.8
STEP_PAUSE = 0.3
CAST_SETTLE = 1.5        # the game closes the menus about 1 s after the cast (24 Oct live)
CAST_POLLS = 5
LIST_DEPTH = 2           # Command menu + spirit list: two Crosses back to the map
EXTRA_CROSSES = 2        # more Crosses while the cursor proves a menu is still open
COMMAND_MENU_ADDRESS = 0x08E4BE34    # u32 entry count, then u32 cursor row (24 Oct dumps)
COMMAND_MENU_BYTES = 8
SPIRIT_ROW_BY_COUNT = {4: 2}         # Move / Attack / Spirit / Info (23 Oct screen, 7 casts 24 Oct)
# (entries, Spirit row) per mech, each from a screenshot of its Command menu.
SPIRIT_ROW_BY_MECH = {"Z Gundam": (5, 3)}     # Move / Attack / Morph / Spirit / Info, 24 Oct


class SpiritIO(act.ActIO, Protocol):
    async def spirits(self, unit_object: int) -> Mapping[str, Any]: ...
    async def spirit_cursor_bytes(self) -> list[int]: ...
    async def command_menu(self) -> tuple[int, int] | None: ...


def decode_command_menu(blob: bytes) -> tuple[int, int] | None:
    """(cursor row, entry count) of the Command menu, or None when implausible."""
    if len(blob) != COMMAND_MENU_BYTES:
        raise ValueError("command menu needs 8 bytes")
    count, row = struct.unpack("<II", blob)
    return (row, count) if 0 < count <= 8 and row < count else None


def spirit_row(count: int, mech_name: str | None) -> int | None:
    """The Spirit entry's row for a menu of `count` entries, None when not screen-checked."""
    known = SPIRIT_ROW_BY_MECH.get(mech_name or "")
    if known is not None:
        return known[1] if known[0] == count else None
    return SPIRIT_ROW_BY_COUNT.get(count)


def _skipped(reason: str, **facts: Any) -> dict[str, Any]:
    return {"status": "skipped", "reason": reason, **facts}


async def _close(io: act.ActIO, presses: int) -> bool:
    try:
        for _ in range(presses):
            await io.press("cross", 2)
            await io.sleep(0.6)
    except act.ActIOError:
        return False
    return True


async def cast_before_attack(io: SpiritIO, unit_object: int, tile: Sequence[int], *,
                             mech_name: str | None = None,
                             reserve: float = 0.0) -> dict[str, Any]:
    """Cast the chosen spirit from the map; `reserve` is the time the attack still needs."""
    if io.time_left() < SPIRIT_NEEDS + reserve:
        return _skipped("no_time")
    try:
        before = await io.spirits(unit_object)
    except act.ActIOError as exc:
        return _skipped("spirits_unreadable", detail=str(exc))
    choice = choose_spirit(before)
    if choice is None:
        return {"status": "none", "sp": before["sp"]}
    name, cost, row = choice["spirit"], choice["cost"], choice["row"]
    if type(row) is not int or not 0 <= row <= MAX_ROW:
        return _skipped("row_too_deep", spirit=name, row=row)
    facts: dict[str, Any] = {"spirit": name, "cost": cost, "row": row}
    seen: list[list[int] | None] = []
    depth = 0
    after: Mapping[str, Any] = before
    try:
        walk = await io.goto([int(tile[0]), int(tile[1])])
        if not walk.get("reached"):
            return _skipped("cursor_did_not_reach_unit", **facts)
        await io.press("circle", 2)
        depth = 1
        await io.sleep(MENU_PAUSE)
        menu = await io.command_menu()
        target = None if menu is None or menu[0] != 0 else spirit_row(menu[1], mech_name)
        if target is None:
            on_map = await _back_to_map(io, tile, depth)
            return _skipped("menu_layout_unknown", entries=menu and menu[1], on_map=on_map,
                            mech=mech_name, **facts)
        for _ in range(target):
            await io.press("down", 2)
            await io.sleep(STEP_PAUSE)
        menu = await io.command_menu()
        facts["menu"] = None if menu is None else [menu[0], menu[1]]
        if menu is None or menu[0] != target:
            on_map = await _back_to_map(io, tile, depth)
            return _skipped("command_row_mismatch", on_map=on_map, **facts)
        await io.press("circle", 2)              # Spirit
        depth = LIST_DEPTH
        await io.sleep(MENU_PAUSE)
        seen.append(await _cursor_bytes(io))     # the list opens on row 0 (23 Oct, screens)
        for _ in range(row):
            await io.press("down", 2)
            await io.sleep(STEP_PAUSE)
        seen.append(await _cursor_bytes(io))
        await io.press("circle", 2)              # casts at once, no Yes/No (24 Oct live)
        await io.sleep(CAST_SETTLE)
        for poll in range(CAST_POLLS):
            try:
                after = await io.spirits(unit_object)
            except act.ActIOError:
                after = before
            if after["sp"] != before["sp"] or poll == CAST_POLLS - 1:
                break
            await io.sleep(1.0)
    except act.ActIOError as exc:
        on_map = await _back_to_map(io, tile, depth)
        return _skipped(f"io_error: {exc}", on_map=on_map, list_bytes=seen, **facts)
    facts["list_bytes"] = seen
    sp = [before["sp"], after["sp"]]
    if after["sp"] == before["sp"]:
        # Nothing was spent, so the list is most likely still open (a refused entry): close it.
        on_map = await _back_to_map(io, tile, LIST_DEPTH)
        return _skipped("cast_not_confirmed", sp=sp, on_map=on_map, **facts)
    facts["on_map"] = await _back_to_map(io, tile, 0)     # a cast closes the menus itself
    if before["sp"] - after["sp"] != cost:
        return {"status": "mismatch", "reason": "spirit_mismatch", "sp": sp, **facts}
    bits = EFFECT_BITS.get(name, 0)
    effects = [before.get("effects"), after.get("effects")]
    confirmed = (type(effects[1]) is int and bits != 0 and effects[1] & bits == bits)
    return {"status": "cast", "sp": sp, "effects": effects, "effect_confirmed": confirmed,
            **facts}


async def _on_map(io: act.ActIO, tile: Sequence[int]) -> bool:
    """The map cursor walks one tile sideways and back (memory-checked by `goto`)."""
    x, y = int(tile[0]), int(tile[1])
    if not (await io.goto([x - 1 if x > 0 else x + 1, y])).get("reached"):
        return False
    return bool((await io.goto([x, y])).get("reached"))


async def _back_to_map(io: act.ActIO, tile: Sequence[int], crosses: int) -> bool:
    """Cross `crosses` times, then prove the map; up to EXTRA_CROSSES more while it is not."""
    await _close(io, crosses)
    for extra in range(EXTRA_CROSSES + 1):
        try:
            if await _on_map(io, tile):
                return True
        except act.ActIOError:
            pass
        if extra < EXTRA_CROSSES:
            await _close(io, 1)
    return False


async def _cursor_bytes(io: SpiritIO) -> list[int] | None:
    """Diagnostics only; a failed read is recorded as None."""
    try:
        return list(await io.spirit_cursor_bytes())
    except act.ActIOError:
        return None
