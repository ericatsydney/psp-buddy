# Weapon memory layout (20 October 2026)

Game: Super Robot Wars Z2 Saisei-hen (ULJS00460, English patch v0.8). The analysis was offline only and used the retained
dumps `local/move-attack-trial-20261017/wrec-run-20261018T2230/ram-*.bin` (Destiny weapon screen) and
`zrec-run-20261018T2315/ram-*.bin` (Z Gundam weapon screen, after its 18 Oct Beam Rifle shot). No emulator was launched.
Local helper scripts are `local/weapon_decode_20261020.py` (decoder) and `local/mips_disasm_20261020.py` (disassembler), both ignored by Git.

## Route in

Public CWCheat codes for ULJS00460, from [gamersky](https://www.gamersky.com/handbook/201207/207648.shtml) and
[jab-guyver](https://jab-guyver.co.kr/7453), use addresses that match our dumps. Each address is `0x08800000` plus the
code offset. For example, the "turn 0" code targets `0x08DF8ADE`, next to our turn counter `0x08DF8ADC`.

- Ammo not decrease, `0x0896BA48`: the ammo routine at `0x0896B9F4` stores `ammo - cost` to a u16 counter. The cost is 9 per
  shot, or 6 or 4 with an ammo-saving modifier, so counters are stored as shots x 9.
- EN not decrease, `0x0896BAC4`: EN is u16 at runtime +0x32 (max at +0x30).
- Range Up, `0x0896C26C`: this is inside the max-range function at `0x0896C1A0`. That function starts from weapon byte +0x0D
  and adds bonuses from three checks (calls with ids 34 and 22, then `0x088E1408`). JIT markers (`0x68xxxxxx`) hide some
  instructions, so a full read needs the live original-code reader.

## Chain

1. Battle actor nodes (16 B, vtable at +0, the existing `actor` list near `0x091C0280`): +4 is a roster-entry pointer and
   +12 is the map object.
2. The roster entry is 12 B in the table at `0x08E6855C` (about 600 rows, one per mech form): mech def, runtime, weapon list.
   - Mech def: s16 mech id at +0 (Destiny 197, Z Gundam 122) and a name pointer at +4.
   - Runtime (0x50 B): HP u32 +0x28 (current) and +0x2C (max); EN u16 +0x30 (max) and +0x32 (current); move u8 +0x15.
     The weapon-upgrade level is a candidate at u8 +0x1D (Destiny 3, Z 0); it is unverified.
3. Weapon list: 21 u32 weapon-record pointers in menu slot order. Empty slots hold 0; Z has slot 2 empty, which matches its menu
   indices 0,1,3..7 at `0x08E39790`. At list +0x54 + 4*i there are pointers to u16 current-ammo counters (x9).
4. Weapon record (44 B, in the database `0x08C8xxxx`-`0x08CBxxxx`):

| Offset | Type | Meaning |
|---|---|---|
| +0x00, +0x04 | u32 | name pointer (full-width Shift-JIS English, NFKC to ASCII) |
| +0x08 | u16 | low bits = slot index; 0x40 = shooting type (melee weapons lack it) |
| +0x0A | u16 | base power |
| +0x0C, +0x0D | u8 | base min / max range |
| +0x0E, +0x10 | s16 | hit / crit modifier |
| +0x12 | u8 | max ammo (0 = EN weapon) |
| +0x13 | u8 | EN cost |
| +0x14 | u8 | will required |
| +0x20 | u8 | bits: 0x01 = P (usable after moving, hypothesis), 0x02 = beam (hypothesis) |

## Checks

- Z Gundam: VulcanCannon 1~2 am10, GrenadeLauncher 1~5 am6, BeamRifle 2~4 am10 with current 9, BeamSaber,
  BeamConfuse (will 110), Hyp.MegaLauncher (EN 40), HyperBeamSaber (will 130). The Beam Rifle 2~4 and 9/10 values match the
  18 Oct attack trial exactly.
- Destiny: CIWS, HiEnergyBeamGun (2~6), FlashEdge2, HiEnergyBeamGun (3~7, EN 35), Arondight, in screen order. The screen
  shows each power +300 and each max range +1, so displayed values include unit modifiers.
- The P bit fits the 18 Oct observation: after moving, Z's Grenade (bit clear) was greyed out, and Vulcan and Beam Rifle (bit set) stayed usable.

## Live check (20 Oct, runs wpn1-run-20261020T1520 and wpn2-run-20261020T1525)

Each run used a fresh verified backup (`backups/wpn1-original-*`, `backups/wpn2-original-*`: SYSTEM, SAVEDATA and PPSSPP_STATE,
44 files, SHA-256) plus the launcher snapshots. Each was view-only (`attack_recon`): goto, open the unit menu, Attack, browse,
and one RAM dump on the weapon screen. Nothing was confirmed. PPSSPP was closed gracefully, and afterwards the originals matched
the wpn2 manifest (44/44).

| | Memory (record) | Screen |
|---|---|---|
| Destiny CIWS | 1900, 1~2, +25/±0, am10, flags S P | 2200, 1~3, +25/±0, 10/10, S P |
| Destiny HiEnergyBeamGun | 2900, 2~6, +15/+5, B | 3200, 2~7, +15/+5, B |
| Destiny FlashEdge2 | 3100, 1~4, +15/+10, P B | 3400, 1~5, +15/+10, P B |
| Destiny HiEnergyBeamGun | 4100, 3~7, +10/±0, EN 35, B, terrain A A C A | 4400, 3~8, +10/±0, EN 35, B, A A C A |
| Destiny Arondight | 4200, 1~2, +20/+15, P B | 4500, 1~3, +20/+15, P B |
| Z Vulcan / Grenade / BeamRifle / BeamSaber / BeamConfuse | 2000 1~2, 2700 1~5, 2800 2~4, 2900 1~2, 3500 1~3, with matching HT/CRT and S/P/B | identical |

Confirmed:
- Hit and crit modifiers, ammo, EN cost and terrain ranks (+0x16..+0x19 = Air, Land, Sea, Space; 1 = A, 2 = B, 3 = C) are read directly.
- Byte +0x20 bits: 0x01 = P, 0x02 = B (beam), 0x08 = S. All eight weapons on screen match.
- Z shows no modifiers. Destiny shows power +300 and max range +1 on every weapon, melee included.
- No cache of effective values exists. With Destiny's weapon screen open, no RAM holds the displayed powers together.

Modifier code:
- The power bonus fits the weapon-upgrade level x 100. The candidate is runtime u8 +0x1D (Destiny 3, Z 0); Strike Freedom 2 and
  Gundam 00 4 are untested.
- The max-range function `0x0896C1A0` adds three bonuses:
  1. Pilot skill id 34 (Newtype-like). Its level indexes the table at `0x08C4E904` (4 B per level, byte +2 = range bonus): +1 at
     levels 7-8 and +2 at level 9. Kamille has level 4, so +0.
  2. Id 22 through `0x089626DC`, +2 (this is what the CWCheat "Range Up" code patches). Shinn has a pilot skill with id 22 at
     level 1, but Destiny shows +1, not +2. A JIT-hidden branch may gate this check.
  3. `0x088E1408`, which calls the general effect engine `0x088E30BC` (parts, upgrade bonuses and so on). Destiny's +1 most
     likely comes from here, possibly a part or a full-upgrade bonus. This is not decoded.
- Pilot skills are (id, level) byte pairs at pilot runtime +0x8E. The pilot runtime is actor +8 -> +4.

## Equipped parts: the range bonus source (20 Oct, later)

- The parts table is at `0x08C5A7F4`, 44 B per part. Fields: +0 name pointer; +4 move (high nibble); +6 max HP; +8 max EN;
  +0x0A defense; +0x0C mobility; +0x0D hit; +0x0E crit; +0x0F weapon range; +0x1A u16 weapon power; +0x1C will required.
  Descriptions are next to the names, for example "Hi・SpecRadar: WeaponRange+1".
- A unit's equipped parts are up to four 1-based ids at runtime +0x38 (0 = empty). The 1-based reading is confirmed by move:
  Wing Gundam, Mercurius and Zangetsu (VernierUnit) and Brasta (AuxiliaryISC) each show runtime move = base + 1. With
  0-based ids, none of the five cases (including Gundam 00) matches.
- Destiny carries Hi・SpecRadar (+1 range) and Propellant・T, which fully explains its +1 max range on screen. Z has no parts.
- `ppsspp_read_weapons` now reports `max_range` = base + part range bonus, the parts list, unconditional part power added to
  `power`, and will-conditional part power (D・Extractor) separately as `conditional_power_bonus`.

## `ppsspp_read_weapons` live (runs wpn4-run-20261020T1616, wpn5-run-20261020T1624)

Each run used a fresh verified backup and was view-only (memory reads only, no game input); afterwards the originals were
unchanged (44/44). Destiny and Z match the 20 Oct screens on every field, including the effective power and Destiny's
1~3 / 2~7 / 1~5 / 3~8 / 1~3. All 26 living units read with no refusal. A call takes about 2.3 s, mostly Node/MCP start-up.

## Not yet known

- The power upgrade field (runtime +0x1D, x100) is verified only on Destiny (3) and Z (0). Per-weapon upgrade increments
  may differ in the game, so `power_resolved` stays false.
- Skill 34 (Newtype-like) at level 7+ and the id-22 check in the range function are not modelled. Units with skill 34
  level 7+ are flagged `range_bonus_resolved: false`. Shinn has id 22 at level 1 and gets no extra range.
- Whether range parts skip range-1 weapons (no such weapon was checked). Effective-ammo rounding with ammo-saving modifiers.
- The meaning of record bytes +0x15 and +0x1A..+0x1F (terrain ranks at +0x16..+0x19 are now confirmed).
- Z's two page-2 weapons (Hyp.MegaLauncher, HyperBeamSaber) were not viewed; the screen needs a page-right input.
- Whether enemy actors always have a weapon list. Enemies in the dumps do, for example Mercurius BeamGun current ammo 7/12.
