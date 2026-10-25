"""Pilot spirit lists read from PSP RAM and the Spirit choice before an attack (no emulator access).

Layout established on 23 October 2026 (docs/research/2026-10-23-spirit-recon.md): battle actor +8 ->
pilot entry, +4 -> pilot runtime. Runtime +0x24 u16 max SP, +0x44 u16 SP (the collector's pilot
record +0x3C), +0x4E u8 level, +0x5C six (spirit id, learn level, SP cost) byte triples in rising
learn level; (0, 255, 255) marks an empty slot. Setsuna's screen (LV36, SP 55/95) lists exactly
the learned triples in stored order with the stored costs: Focus 15, Sense 20, Yell 35. Ids are
named only where a screen proved them. Runtime +0x14 u16 is the active-effect mask in the order of
the spirit screen's effect strip (heat, soul, Flash, ..., Focus, Aim, ...): a live Sense cast on
24 Oct set it 0 -> 0x44 (Flash bit 2 + Aim bit 6, both lit on the strip, Sense greyed). The Focus
bit (5) follows the strip order and is not yet observed.
"""

import struct
from collections.abc import Awaitable, Callable, Collection, Mapping
from typing import Any

from .weapons import RAM_END, RAM_START

PILOT_BLOB_SIZE = 0x70
MAX_SP_OFFSET = 0x24
SP_OFFSET = 0x44
LEVEL_OFFSET = 0x4E
SPIRITS_OFFSET = 0x5C
EFFECTS_OFFSET = 0x14
# Sense = Flash 0x04 + Aim 0x40 (24 Oct live). Alert = Flash 0x04 (25 Oct live cast: SP 19 -> 4,
# mask 0 -> 0x04). Invincible = the 鉄 bit 4 by the effect-strip order, not observed
# (no ally has it).
EFFECT_BITS = {"Alert": 0x04, "Invincible": 0x10, "Focus": 0x20, "Sense": 0x44}
SPIRIT_SLOTS = 6
EMPTY_LEVEL = 255
MAX_LEVEL = 99
# 6 and 9 from Setsuna's spirit screen (23 Oct); 3 and 5 from Wing Gundam Zero's pilot page (25 Oct:
# Guard 15, Alert 10, Strike 20, Bless 45 = ids 5, 3, 7, 31). This English patch shows 鉄壁
# as "Guard".
NAMES = {3: "Alert", 5: "Invincible", 6: "Focus", 9: "Sense"}
# User rule (23 Oct, extended 25 Oct): one spirit per attack, the first learned, affordable and not
# active; Alert and Invincible serve pilots without Sense or Focus.
PREFERENCE = ("Sense", "Focus", "Alert", "Invincible")
# Spirit-list cursor row candidates (u8). In the five recon dumps of 23/24 Oct both equal the
# list row while the list is open, but on a fresh launch (m11live1, 24 Oct) they did not read 0
# on an opened list in 3 of 4 casts. Recorded as diagnostics only, never used to decide.
LIST_ROW_ADDRESSES = (0x091FF510, 0x08DE6BF4)

Reader = Callable[[int, int], Awaitable[bytes]]


def decode_pilot(blob: bytes) -> dict[str, Any]:
    """Level, SP and the spirit list (with menu rows of the learned ones) of one pilot runtime."""
    if len(blob) != PILOT_BLOB_SIZE:
        raise ValueError("pilot runtime size")
    max_sp, sp = (struct.unpack_from("<H", blob, o)[0] for o in (MAX_SP_OFFSET, SP_OFFSET))
    level = blob[LEVEL_OFFSET]
    if not 1 <= level <= MAX_LEVEL or sp > max_sp:
        raise ValueError("implausible pilot level or SP")
    rows: list[dict[str, Any]] = []
    previous, row = 0, 0
    for slot in range(SPIRIT_SLOTS):
        spirit, learn, cost = blob[SPIRITS_OFFSET + 3 * slot:SPIRITS_OFFSET + 3 * slot + 3]
        if learn == EMPTY_LEVEL:
            continue
        if not spirit or not cost or learn < previous:
            raise ValueError("implausible spirit list")
        previous = learn
        learned = level >= learn
        rows.append({"id": spirit, "name": NAMES.get(spirit), "learn_level": learn, "cost": cost,
                     "learned": learned, "row": row if learned else None})
        row += learned
    effects = struct.unpack_from("<H", blob, EFFECTS_OFFSET)[0]
    active = sorted(name for name, bits in EFFECT_BITS.items() if effects & bits == bits)
    return {"level": level, "sp": sp, "max_sp": max_sp, "spirits": rows, "effects": effects,
            "active": active}


async def read_pilot_spirits(read: Reader, actor: int) -> dict[str, Any]:
    """Follow actor +8 -> +4 to the pilot runtime and decode it (one short pause by the caller)."""
    address = actor + 8
    for offset, size in ((4, 8), (0, PILOT_BLOB_SIZE)):     # pilot entry, then pilot runtime
        raw = await read(address, 4)
        if len(raw) != 4:
            raise ValueError("short memory read")
        pointer = struct.unpack("<I", raw)[0]
        if not RAM_START <= pointer <= RAM_END - size or pointer % 4:
            raise ValueError("invalid pilot pointer")
        address = pointer + offset
    blob = await read(address, PILOT_BLOB_SIZE)
    return decode_pilot(blob)


def choose_spirit(pilot: Mapping[str, Any], *,
                  active: Collection[str] = ()) -> dict[str, Any] | None:
    """The first of PREFERENCE that is learned, affordable and not active, else None."""
    active = {*active, *pilot.get("active", ())}
    for name in PREFERENCE:
        for spirit in pilot["spirits"]:
            if (spirit["name"] == name and spirit["learned"] and name not in active
                    and spirit["cost"] <= pilot["sp"]):
                return {"spirit": name, "id": spirit["id"], "cost": spirit["cost"],
                        "row": spirit["row"]}
    return None
