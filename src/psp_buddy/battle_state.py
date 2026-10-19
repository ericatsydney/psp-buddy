"""Pure decoders for live battle state read from PSP RAM (no I/O, no emulator access).

Addresses are those established on 18-19 October 2026 (see docs/progress.md): map cell table,
dimensions, map cursor tile and the turn counter. Every decoder validates sizes and ranges.
"""

import struct

CELL_SIZE = 16
MAX_CELLS = 1024                    # the game's cell window is 0x4000 bytes (1024 cells)
MAX_TURN = 999
CELL_TABLE_ADDRESS = 0x08E4EA94
MAP_WIDTH_ADDRESS = 0x08E52A94      # u16 width, u16 height follow each other
CURSOR_ADDRESS = 0x096007C4         # u16 x, u16 y
TURN_ADDRESS = 0x08DF8ADC           # u16 turn, u16 running total
TERRAIN_CLASSES = {1: "space", 2: "asteroid", 18: "debris"}
_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


def _symbol(value: int) -> str:
    """One character per tile: 0 -> '.', 1..35 -> base-36, anything larger -> '#'."""
    if value == 0:
        return "."
    return _DIGITS[value] if value < len(_DIGITS) else "#"


def check_dimensions(width: int, height: int) -> None:
    if (type(width) is not int or type(height) is not int or width < 1 or height < 1
            or width * height > MAX_CELLS):
        raise ValueError("invalid map dimensions")


def decode_map(blob: bytes, width: int, height: int) -> dict[str, object]:
    """Terrain class (cell byte 0) and move cost (cell byte 12) as one string per map row."""
    check_dimensions(width, height)
    if len(blob) != CELL_SIZE * width * height:
        raise ValueError("cell table has the wrong size")
    terrain_rows: list[str] = []
    cost_rows: list[str] = []
    seen: set[int] = set()
    for y in range(height):
        terrain = ""
        cost = ""
        for x in range(width):
            base = CELL_SIZE * (y * width + x)
            terrain += _symbol(blob[base])
            cost += _symbol(blob[base + 12])
            if blob[base]:
                seen.add(blob[base])
        terrain_rows.append(terrain)
        cost_rows.append(cost)
    return {
        "width": width,
        "height": height,
        "terrain_rows": terrain_rows,
        "cost_rows": cost_rows,
        "terrain_classes": {_symbol(v): TERRAIN_CLASSES.get(v, "unknown") for v in sorted(seen)},
    }


def reachable_tiles(state: dict[str, object]) -> list[dict[str, int]]:
    """Tiles with a non-zero move cost; non-empty only while a unit's Move range is displayed."""
    rows = state["cost_rows"]
    assert isinstance(rows, list)
    result: list[dict[str, int]] = []
    for y, row in enumerate(rows):
        for x, symbol in enumerate(row):
            if symbol != ".":
                result.append({"x": x, "y": y, "cost": _DIGITS.index(symbol) if symbol in _DIGITS
                               else -1})
    return result


def decode_cursor(blob: bytes, width: int, height: int) -> dict[str, int]:
    check_dimensions(width, height)
    if len(blob) != 4:
        raise ValueError("cursor field must be 4 bytes")
    x, y = struct.unpack("<HH", blob)
    if x >= width or y >= height:
        raise ValueError("cursor tile outside the map")
    return {"x": x, "y": y}


def decode_turn(blob: bytes) -> dict[str, int]:
    if len(blob) != 4:
        raise ValueError("turn field must be 4 bytes")
    turn, total = struct.unpack("<HH", blob)
    if not 1 <= turn <= MAX_TURN:
        raise ValueError("implausible turn number")
    return {"turn": turn, "running_total": total}
