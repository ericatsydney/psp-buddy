# Damage model — offline inventory (M8 task 1, 21 Oct 2026)

No emulator was launched. Sources: retained `act5-run-20261020T2236` (act5-r4.json), `zatk-run-20261018T2120`
(stage-03/05.json), `spd5-run-20261021T2112` (act result), the 20 Oct weapon note and the weapon reads.

## Observed attack results (HP change of the unit that took the hit)

| Source | Attacker, weapon (effective power) | Receiver (mech/pilot) | HP change | Notes |
|---|---|---|---|---|
| zatk 18 Oct | Z Gundam, Beam Rifle (2800) | 149301208 (160/191) | 2603 -> 450 = **2153** | support defender took the shot |
| act5 20 Oct | Z Gundam, Beam Rifle (2800) | 149301312 (160/191) | 4104 -> 1954 = **2150** | support defender took the shot |
| act5 / zatk | Euclid counters on Z | Z Gundam (122/134) | 4700 -> 1730 = 2970; 4700 -> 1119 = 3581 | counter weapons not recorded |
| spd5 21 Oct | Destiny, FlashEdge2 (3400+300) | Mercurius | none (EN only) | missed (60% forecast) |
| earlier | Destiny, HiEnergyBeamGun (4400+300) | Mercurius | none | missed (42% forecast) |

## Findings

- The in-game forecast shows no damage number (21 Oct screenshot: hit %, HP/EN, weapon names, Start), so there is no
  on-screen ground truth for a forecast field; truth is the HP delta after a hit.
- Only **one comparable pair** exists (same attacker and weapon, same target type): 2153 and 2150 (difference 3).
  Everything else lacks the counter weapon, the target defense or a hit. A formula needs power, attacker pilot stats,
  target mech defense (+0x0A of the mech record), pilot stats, terrain and size modifiers: unknowns outnumber data points.
- Damage is about 77% of weapon power for Beam Rifle against mech 160. A single ratio is not a model.

## Gate outcome (spec D1)

No exact formula can be validated from retained data. **Fallback adopted:** expected damage = hit% x effective weapon power,
used only to rank options (`damage_model: "power"`). To enable a real model later, M8 task 3 logs every fired act's
(attacker, weapon, effective power, target mech/pilot ids, target terrain, HP delta, hit/miss) to `damage-log.jsonl` in the run
folder. Fit a formula once at least about 15 hits across 4+ weapon powers and 4+ target mechs are collected, then compare it
against the memory fields (mech defense, pilot stats) before trusting it.
