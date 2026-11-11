# Effective move (10 Nov 2026)

Why Hyaku Shiki's read move (6) was one short of the game's Move range (7) in run s2o.
Offline only: disassembly of the s2o checkpoint RAM (`local/checkpoints/s2o`), no game launch.

## The game's move function, `0x0896A090`

Argument: the unit (`+4` roster entry, `+8` pilot). Ten call sites. In order:

1. Start from unit runtime `+0x15`. This already includes equipped parts (20 Oct finding).
2. **+3** if effect id 10 is active. `0x089660B0` ORs the pilots' effect masks (pilot runtime `+0x14`)
   and tests the table at `0x08C49858`, where id 10 means bit number 8 (mask `0x80`). Probably the
   Accel spirit, not confirmed.
3. **Pilot skill 21** (byte pairs at pilot runtime `+0x8E`, level above 0): **+1**, or **+2** when
   will (`+0x46`) is at least 130 and `0x08861E54(pilot)` is true.
4. A bonus from the table at `0x08C50A98` (24 B rows, `+0x10` s16), only when the high nibble of runtime
   `+0x45` is non-zero and two further checks pass. That nibble is 0 on all 24 allies in this save.
5. A positive result from the general effect engine (`0x088E1458` -> `0x088E30BC`). Not decoded.

## Fit against the live range marks (s2o)

| Unit | Runtime move | Skill 21 | Game range (furthest marked tile) |
|---|---|---|---|
| Hyaku Shiki | 6 | yes | 7 |
| Altron | 7 | no | 7 |
| Deathscythe Hell | 7 | no | 7 |

The only other ally with skill 21 in this save is VF-25F Messiah (runtime 8, so 9 expected). Its one
logged move was 8 tiles, which neither confirms nor refutes it.

## Not known

- What `0x08861E54` tests, so the +2 at will 130 is not fully decoded.
- Which parts of steps 4 and 5 ever apply. One unit is the only positive case for skill 21.
- Whether any of the ten callers uses a different value for the drawn range.

Reader today: `weapons.read_unit_weapons` returns runtime `+0x15` only. `act.stop_range` compares
tiles to it, and `tactics.foe_reach_of` uses it for how far a foe can reach.
