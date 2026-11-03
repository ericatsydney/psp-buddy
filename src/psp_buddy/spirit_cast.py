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
a menu that still does not close makes the caller stop the turn. When only the Command menu was
open (no cast), memory proves the map first (no UI window, cursor on the unit; user, 1 Nov) and the
cursor walk is the fallback; a mech whose layout is unknown is not tried again in the same run.
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
# The post-move menu (Attack / ... / Standby) has its own slot 0x80 on, same layout; the slot
# above keeps the earlier Command menu meanwhile (31 Oct recon m14rec3, six RAM dumps).
POST_MOVE_MENU_ADDRESS = 0x08E4BEB4
SPIRIT_ROW_BY_COUNT = {4: 2}         # Move / Attack / Spirit / Info (23 Oct screen, 7 casts 24 Oct)
# {entries: Spirit row} per mech, each from a screenshot of its Command menu; a mech listed here
# with another entry count is unknown (the count-only table is not used for it).
SPIRIT_ROW_BY_MECH = {
    "Z Gundam": {5: 3,                  # Move / Attack / Morph / Spirit / Info, 24 Oct
                 4: 2},                 # Move / Morph / Spirit / Info, 3 Nov m16-rec-menus
    # 3 Nov recon m16-rec-michel / -alto (no foe in reach): Move / Land / Morph / Spirit / Info
    "VF25GMessiahF・TP": {5: 3},
    "VF-25F Messiah F/TP": {5: 3},
    "AriosGundam": {5: 3},              # m16-rec-arios: Move / Attack / Land / Spirit / Info
    # 3 Nov recon m16-rec-menus (turn-1 start, no foe in reach):
    "VF19KaiValkyrieF": {6: 4},         # Move / Sing / Land / Morph / Spirit / Info
    "AltronGundam": {3: 1},             # Move / Spirit / Info
    "DeathscytheHell": {3: 1},          # Move / Spirit / Info
    "WingGundamZero": {5: 3},           # Move / Land / Morph / Spirit / Info
}
# A unit with two pilots opens SELECT-PILOT before the list (3 Nov recon, 00 Raiser: Setsuna,
# the unit's pilot, on top). UI-pool windows: pilot select and spirit list.
PILOT_SELECT_WINDOW, SPIRIT_LIST_WINDOW = 0x08E4D090, 0x08E4D208


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


# M16 (3 Nov): each menu slot holds a u32 entry bitmask 8 bytes before its count; entries are
# listed in rising bit order. Bits from retained dumps: Move 2, Attack 3, Morph 14, Spirit 23,
# Standby 25, Retrieve 26, Info 27 (Gundam 00 0x0880000C, Z Gundam 0x0880400C, a ship 0x0C80000C,
# post-move Standby / Retrieve 0x06000000 on m16-c).
COMMAND_MASK_ADDRESS = COMMAND_MENU_ADDRESS - 8
POST_MOVE_MASK_ADDRESS = POST_MOVE_MENU_ADDRESS - 8
SPIRIT_BIT, STANDBY_BIT = 23, 25


def entry_row(mask: int, count: int, bit: int) -> int | None:
    """Row of the entry `bit` when the mask lists exactly `count` entries and has it, else None."""
    if not 0 <= mask < 1 << 32 or not mask >> bit & 1 or bin(mask).count("1") != count:
        return None
    return bin(mask & ((1 << bit) - 1)).count("1")


async def menu_masks(io: act.ActIO) -> tuple[int, int] | None:
    """(Command-menu mask, post-move-menu mask), or None without a reader or on a failed read."""
    reader = getattr(io, "menu_masks", None)
    if reader is None:
        return None
    try:
        masks: tuple[int, int] = await reader()
    except act.ActIOError:
        return None
    return masks


def spirit_row(count: int, mech_name: str | None) -> int | None:
    """The Spirit entry's row for a menu of `count` entries, None when not screen-checked."""
    known = SPIRIT_ROW_BY_MECH.get(mech_name or "")
    if known is not None:
        return known.get(count)
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
                             reserve: float = 0.0,
                             skip_mechs: set[str] | None = None) -> dict[str, Any]:
    """Cast the chosen spirit from the map; `reserve` is the time the attack still needs.
    `skip_mechs` (per run) holds mechs whose Command menu layout proved unknown: they are not
    tried again (user, 1 Nov: each try opened, closed and re-proved the menu for nothing)."""
    if mech_name and skip_mechs is not None and mech_name in skip_mechs:
        return _skipped("menu_layout_unknown", mech=mech_name, cached=True)
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
        masks = await menu_masks(io)
        target = None
        if menu is not None and menu[0] == 0:
            target = (spirit_row(menu[1], mech_name) if masks is None
                      else entry_row(masks[0], menu[1], SPIRIT_BIT))
        if target is None:
            on_map = await _back_to_map(io, tile, depth, memory_first=True)
            # Only a plausible read on row 0 shows the layout itself is unknown; a failed read
            # or another row is no reason to skip this mech for the rest of the run.
            # With the bitmask the row is worked out per menu: no per-run skip (review 3 Nov).
            if (mech_name and skip_mechs is not None and menu is not None and menu[0] == 0
                    and masks is None):
                skip_mechs.add(mech_name)
            return _skipped("menu_layout_unknown", entries=menu and menu[1], on_map=on_map,
                            mech=mech_name, **facts)
        for _ in range(target):
            await io.press("down", 2)
            await io.sleep(STEP_PAUSE)
        menu = await io.command_menu()
        facts["menu"] = None if menu is None else [menu[0], menu[1]]
        if menu is None or menu[0] != target:
            on_map = await _back_to_map(io, tile, depth, memory_first=True)
            return _skipped("command_row_mismatch", on_map=on_map, **facts)
        await io.press("circle", 2)              # Spirit
        depth = LIST_DEPTH
        await io.sleep(MENU_PAUSE)
        if await _pilot_select(io):
            await io.press("circle", 2)          # the first pilot: the one whose SP is read
            depth = LIST_DEPTH + 1
            facts["pilot_select"] = True
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
        on_map = await _back_to_map(io, tile, depth)
        return _skipped("cast_not_confirmed", sp=sp, on_map=on_map, **facts)
    facts["on_map"] = await _back_to_map(io, tile, 0)     # a cast closes the menus itself
    if before["sp"] - after["sp"] != cost:
        return {"status": "mismatch", "reason": "spirit_mismatch", "sp": sp, **facts}
    bits = EFFECT_BITS.get(name, 0)
    effects = [before.get("effects"), after.get("effects")]
    confirmed = (type(effects[1]) is int and bits != 0 and effects[1] & bits == bits)
    return {"status": "cast", "sp": sp, "effects": effects, "effect_confirmed": confirmed,
            **facts}


async def _pilot_select(io: act.ActIO) -> bool:
    """SELECT-PILOT is open and the spirit list is not (UI pool); False when unsure."""
    try:
        windows = (await io.state()).get("ui_windows")
    except act.ActIOError:
        return False
    return (isinstance(windows, list) and PILOT_SELECT_WINDOW in windows
            and SPIRIT_LIST_WINDOW not in windows)


async def _on_map(io: act.ActIO, tile: Sequence[int]) -> bool:
    """The map cursor walks one tile sideways and back (memory-checked by `goto`)."""
    x, y = int(tile[0]), int(tile[1])
    if not (await io.goto([x - 1 if x > 0 else x + 1, y])).get("reached"):
        return False
    return bool((await io.goto([x, y])).get("reached"))


async def _map_in_memory(io: act.ActIO, tile: Sequence[int]) -> bool:
    """No UI window open (M15 pool) and the cursor still on the unit; False when unsure."""
    try:
        state = await io.state()
    except act.ActIOError:
        return False
    cursor = state.get("cursor")
    return (state.get("screen") == "no_menu" and isinstance(cursor, Mapping)
            and [cursor.get("x"), cursor.get("y")] == [int(tile[0]), int(tile[1])])


async def _back_to_map(io: act.ActIO, tile: Sequence[int], crosses: int, *,
                       memory_first: bool = False) -> bool:
    """Cross `crosses` times, then prove the map; up to EXTRA_CROSSES more while it is not.
    `memory_first`: only the Command menu was open (no cast, no list), so a Cross cannot have
    started a dialogue and memory proves the map; the cursor walk stays the fallback."""
    await _close(io, crosses)
    if memory_first and await _map_in_memory(io, tile):
        return True
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
