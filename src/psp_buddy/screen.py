"""M15 P2: which screen is open, from the game's UI window pool (M15 Task 1, 31 Oct).

Pure logic. The pool holds 32 nodes of 12 bytes `[slot, next, prev]` from NODES_START; node k's
slot word (SLOTS_START + 4k) points at a window object. Free nodes form a list from FREE_HEAD whose
length is FREE_COUNT. The allocated objects name the screen; their addresses (and type words) were
the same on stage 23 and stage 33 across 33 retained RAM dumps and the stage-33 checkpoint
(docs/research/2026-11-01-m15-screen-signatures.md). Anything else is `unknown`.

Not separated by the pool: the bare map and the range view left after a Command menu closes
(m14s33a); both read `no_menu`. Command and system menus share one window (`unit_commands`).
"""

import struct
from typing import Any

RAM_BASE = 0x08800000
SLOTS_START = 0x08E4B96C
NODES_START = 0x08E4B9F8
NODE_COUNT = 32
FREE_COUNT = 0x08E4BB9C
FREE_HEAD = 0x08E4BBAC
REGION_START, REGION_END = SLOTS_START, FREE_HEAD + 4     # one read covers the whole pool

ROOT = 0x08E4BD0C               # always allocated
AMBIENT = frozenset({0x08E4CED4})   # seen on the stage-33 map after the back-out; not a menu
COMMAND, MENU2, RANGE, WEAPONS, TARGETS, SPIRITS = (
    0x08E4BDDC, 0x08E4BE5C, 0x08E4BF6C, 0x08E4C5C4, 0x08E4C67C, 0x08E4D208)

SCREENS: dict[frozenset[int], str] = {
    frozenset(): "no_menu",
    frozenset({COMMAND}): "unit_commands",
    frozenset({COMMAND, RANGE}): "move_range",
    frozenset({COMMAND, WEAPONS}): "weapon_list",
    frozenset({COMMAND, WEAPONS, TARGETS}): "target_select",
    frozenset({COMMAND, MENU2, RANGE}): "post_move_menu",
    frozenset({COMMAND, SPIRITS}): "spirit_list",
}
LAYERS = {name: len(objects) for objects, name in SCREENS.items()}

# One Cross closes the top window (m14s33a, m14rec3). Only back-outs seen live are listed; a
# post-move menu (Cross may undo the move) and the spirit list are not proven and get none.
BACKOUT: dict[str, list[tuple[str, str]]] = {
    "no_menu": [],
    "unit_commands": [("close_command_menu", "no_menu")],
    "weapon_list": [("cancel", "unit_commands"), ("close_command_menu", "no_menu")],
    "target_select": [("cancel", "weapon_list"), ("cancel", "unit_commands"),
                      ("close_command_menu", "no_menu")],
    "move_range": [("cancel", "unit_commands"), ("close_command_menu", "no_menu")],
}


def open_windows(blob: bytes, base: int = RAM_BASE) -> list[int]:
    """The window objects of the allocated pool nodes (root included), from memory starting at
    `base` (a whole RAM image, or one read of REGION_START..REGION_END)."""
    def u32(address: int) -> int:
        offset = address - base
        if offset < 0 or offset + 4 > len(blob):
            raise ValueError("UI pool outside the read")
        value: int = struct.unpack_from("<I", blob, offset)[0]
        return value

    nodes = [NODES_START + 12 * k for k in range(NODE_COUNT)]
    free: set[int] = set()
    node = u32(FREE_HEAD)
    while node in nodes:
        if node in free:
            raise ValueError("UI pool free list loops")
        free.add(node)
        node = u32(node + 4)
    if len(free) != u32(FREE_COUNT):
        raise ValueError("UI pool free list disagrees with its count")
    return [u32(u32(n)) for n in nodes if n not in free]


def classify(objects: list[int]) -> str:
    if objects.count(ROOT) != 1 or len(set(objects)) != len(objects):
        return "unknown"
    return SCREENS.get(frozenset(objects) - {ROOT} - AMBIENT, "unknown")


def layers(name: str) -> int | None:
    return LAYERS.get(name)


def backout(name: str) -> list[dict[str, Any]] | None:
    """Cross presses that close the screen down to the map, each with the screen it must leave;
    None when no back-out is proven for it."""
    steps = BACKOUT.get(name)
    if steps is None:
        return None
    return [{"button": "cross", "purpose": purpose, "expect": expect}
            for purpose, expect in steps]
