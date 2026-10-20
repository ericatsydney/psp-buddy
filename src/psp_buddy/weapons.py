"""Weapon data read from PSP RAM by following the game's own pointers (no emulator access here).

Layout established on 20 October 2026 (docs/research/2026-10-20-weapon-memory.md):
battle actor +4 -> roster entry (mech def, runtime, weapon list); the weapon list holds 21 record
pointers in menu-slot order (0 = empty slot) followed by 21 pointers to u16 ammo counters that
count shots x 9. Weapon records are shared static game data. Displayed power adds the unit's
weapon-upgrade level x 100 (candidate field, verified on two units) and unconditional part power.
Displayed max range adds the range bonus of the equipped parts: up to four 1-based part ids at
runtime +0x38 index the static parts table (verified: Destiny's Hi-SpecRadar gives the +1 seen on
screen; part move bonuses match runtime move for five units). A Newtype-like pilot skill (id 34)
at level 7+ can add range to some weapons, which is not modelled, so such units are flagged.
"""

import struct
import unicodedata
from collections.abc import Awaitable, Callable

RAM_START = 0x08800000
RAM_END = 0x0A000000
ACTOR_SIZE = 16
ROSTER_ENTRY_SIZE = 12
MECH_DEF_SIZE = 8
RUNTIME_SIZE = 0x50
WEAPON_RECORD_SIZE = 44
WEAPON_SLOTS = 21
WEAPON_LIST_SIZE = 8 * WEAPON_SLOTS          # record pointers, then ammo-counter pointers
PILOT_SKILLS_OFFSET = 0x8E
PILOT_SKILL_PAIRS = 8
NAME_MAX = 64
AMMO_UNIT = 9                                 # the ammo routine subtracts 9 per normal shot
POWER_PER_UPGRADE = 100
PARTS_TABLE_ADDRESS = 0x08C5A7F4
PART_SIZE = 0x2C
PART_SLOTS = 4
PARTS_OFFSET = 0x38
MAX_PART_ID = 80
NEWTYPE_SKILL = 34
NEWTYPE_RANGE_LEVEL = 7
MAX_UPGRADE_LEVEL = 15
MAX_RANGE = 99
TERRAIN_RANKS = "-ABCDS"

Reader = Callable[[int, int], Awaitable[bytes]]


def _pointer(value: int, size: int, align: int, what: str) -> int:
    if not (RAM_START <= value and value + size <= RAM_END) or value % align:
        raise ValueError(f"invalid {what} pointer")
    return value


async def _read(read: Reader, address: int, size: int) -> bytes:
    data = await read(address, size)
    if len(data) != size:
        raise ValueError("short memory read")
    return data


def decode_name(raw: bytes) -> str:
    """Full-width Shift-JIS game text up to its NUL, normalised to plain ASCII where possible."""
    end = raw.find(b"\x00", 0, NAME_MAX)
    if end <= 0:
        raise ValueError("missing or unterminated name")
    try:
        text = unicodedata.normalize("NFKC", raw[:end].decode("cp932"))
    except UnicodeDecodeError as exc:
        raise ValueError("name is not valid Shift-JIS") from exc
    if not text.strip() or not text.isprintable():
        raise ValueError("implausible name")
    return text


def decode_weapon_record(record: bytes, slot: int) -> dict[str, object]:
    """Static weapon fields; the record's own slot field must match the list slot it came from."""
    if len(record) != WEAPON_RECORD_SIZE:
        raise ValueError("weapon record has the wrong size")
    kind, power, min_range, max_range, hit, crit = struct.unpack_from("<HHBBhh", record, 8)
    if kind & 0x3F != slot:
        raise ValueError("weapon record does not belong to this slot")
    if not 1 <= min_range <= max_range <= MAX_RANGE:
        raise ValueError("implausible weapon range")
    terrain = record[22:26]
    if any(rank >= len(TERRAIN_RANKS) for rank in terrain):
        raise ValueError("implausible terrain rank")
    bits = record[32]
    return {
        "slot": slot,
        "base_power": power,
        "min_range": min_range,
        "max_range_base": max_range,
        "hit": hit,
        "crit": crit,
        "max_ammo": record[18],
        "en_cost": record[19],
        "will": record[20],
        "terrain": "".join(TERRAIN_RANKS[rank] for rank in terrain),   # air, land, sea, space
        "flags": {"p": bool(bits & 1), "beam": bool(bits & 2), "s": bool(bits & 8),
                  "shooting": bool(kind & 0x40)},
    }


async def _pilot_skills(read: Reader, pilot: int) -> list[dict[str, int]] | None:
    """Pilot skill (id, level) pairs; None when the unit has no readable pilot (auxiliary data)."""
    try:
        _pointer(pilot, 8, 4, "pilot descriptor")
        pilot_runtime = struct.unpack_from("<I", await _read(read, pilot, 8), 4)[0]
        address = _pointer(pilot_runtime + PILOT_SKILLS_OFFSET, 2 * PILOT_SKILL_PAIRS, 2,
                           "pilot runtime")
    except ValueError:
        return None
    pairs = await _read(read, address, 2 * PILOT_SKILL_PAIRS)
    return [{"id": pairs[i] & 0x3F, "level": pairs[i + 1]}
            for i in range(0, len(pairs), 2) if pairs[i] and pairs[i + 1]]


async def _parts(read: Reader, ids: bytes) -> tuple[list[dict[str, object]], int, int, int]:
    """Equipped parts (1-based ids, 0 = empty slot); also returns the summed range bonus, the
    unconditional weapon-power bonus and the will-conditional power bonus."""
    parts: list[dict[str, object]] = []
    range_bonus = power = conditional = 0
    for part_id in ids:
        if not part_id:
            continue
        if part_id > MAX_PART_ID:
            raise ValueError("implausible part id")
        record = await _read(read, PARTS_TABLE_ADDRESS + PART_SIZE * (part_id - 1), PART_SIZE)
        name = _pointer(struct.unpack_from("<I", record)[0], NAME_MAX, 1, "part name")
        weapon_power = struct.unpack_from("<H", record, 0x1A)[0]
        range_bonus += record[0x0F]
        if record[0x1C]:
            conditional += weapon_power
        else:
            power += weapon_power
        parts.append({
            "id": part_id,
            "name": decode_name(await _read(read, name, NAME_MAX)),
            "range_bonus": record[0x0F],
            "weapon_power": weapon_power,
            "will_required": record[0x1C],
        })
    return parts, range_bonus, power, conditional


async def read_unit_weapons(read: Reader, actor: int) -> dict[str, object]:
    """Follow one battle actor to its mech, resources, pilot skills and weapons."""
    _pointer(actor, ACTOR_SIZE, 4, "actor")
    _, entry, pilot = struct.unpack("<III", (await _read(read, actor, ACTOR_SIZE))[:12])
    entry = _pointer(entry, ROSTER_ENTRY_SIZE, 4, "roster entry")
    mech, runtime, weapon_list = struct.unpack("<III", await _read(read, entry, ROSTER_ENTRY_SIZE))
    mech = _pointer(mech, MECH_DEF_SIZE, 4, "mech definition")
    runtime = _pointer(runtime, RUNTIME_SIZE, 4, "unit runtime")
    weapon_list = _pointer(weapon_list, WEAPON_LIST_SIZE, 4, "weapon list")
    mech_id, mech_name = struct.unpack("<hxxI", await _read(read, mech, MECH_DEF_SIZE))
    name_text = decode_name(await _read(read, _pointer(mech_name, NAME_MAX, 1, "name"), NAME_MAX))
    resources = await _read(read, runtime, RUNTIME_SIZE)
    max_hp, hp = struct.unpack_from("<II", resources, 0x28)
    max_en, en = struct.unpack_from("<HH", resources, 0x30)
    if not hp <= max_hp or not en <= max_en:
        raise ValueError("inconsistent unit runtime")
    # Candidate field (verified on two units only): a value outside the plausible range is
    # reported but not applied, rather than refusing the whole read.
    upgrade_raw = resources[0x1D]
    upgrade = upgrade_raw if upgrade_raw <= MAX_UPGRADE_LEVEL else 0
    skills = await _pilot_skills(read, pilot)
    parts, range_bonus, part_power, conditional_power = await _parts(
        read, resources[PARTS_OFFSET:PARTS_OFFSET + PART_SLOTS])
    range_resolved = not any(skill["id"] == NEWTYPE_SKILL and skill["level"] >= NEWTYPE_RANGE_LEVEL
                             for skill in skills or [])
    pointers = struct.unpack(f"<{2 * WEAPON_SLOTS}I", await _read(read, weapon_list,
                                                                  WEAPON_LIST_SIZE))
    weapons: list[dict[str, object]] = []
    for slot in range(WEAPON_SLOTS):
        if not pointers[slot]:
            continue
        address = _pointer(pointers[slot], WEAPON_RECORD_SIZE, 4, "weapon record")
        record = await _read(read, address, WEAPON_RECORD_SIZE)
        weapon = decode_weapon_record(record, slot)
        name_address = _pointer(struct.unpack_from("<I", record)[0], NAME_MAX, 1, "name")
        base_power, max_ammo = struct.unpack_from("<H", record, 10)[0], record[18]
        ammo: int | None = None
        raw: int | None = None
        if max_ammo:
            counter = _pointer(pointers[WEAPON_SLOTS + slot], 2, 2, "ammo counter")
            raw = struct.unpack("<H", await _read(read, counter, 2))[0]
            # Parts can raise capacity above the record's base maximum, so this is not checked.
            ammo = raw // AMMO_UNIT
        weapons.append({
            "name": decode_name(await _read(read, name_address, NAME_MAX)),
            **weapon,
            "power": base_power + POWER_PER_UPGRADE * upgrade + part_power,
            "power_resolved": False,           # upgrade field is a candidate, see the module note
            "max_range": record[13] + range_bonus,
            "range_bonus_resolved": range_resolved,
            "ammo": ammo,
            "ammo_raw": raw,
        })
    return {
        "actor": actor,
        "mech_id": mech_id,
        "mech_name": name_text,
        "hp": hp,
        "max_hp": max_hp,
        "en": en,
        "max_en": max_en,
        "move": resources[0x15],
        "upgrade_level_candidate": upgrade_raw,
        "pilot_skills": skills,
        "parts": parts,
        "conditional_power_bonus": conditional_power,
        "weapons": weapons,
        "note": ("power = base + 100 x upgrade level (candidate) + unconditional part power; "
                 "max_range = base + part range bonus"),
    }
