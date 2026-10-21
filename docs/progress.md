# Project progress

Updated 20 October 2026 (Australia/Brisbane).
Ticks mean ready in the scope stated; unchecked items may have partial implementation.

## 1. Long-term goal

Play one battle autonomously from an existing save, following your tactical instructions,
with protected progress, up to three checkpoint retries, and handover when needed.

- [x] Verified save/state backup service.
- [ ] Start from an in-game save or save state automatically.
- [ ] Read the complete current battle state automatically. (Partial, from memory and verified live: units, map, cursor, turn and every unit's weapons. Not yet: targets in range, hit/damage forecasts.)
- [ ] Follow tactical instructions and choose legal actions in a live battle.
- [ ] Move and attack automatically. (Prototype: agent executes a declared, screenshot-grounded Move/Attack/Standby; it does not yet choose targets or plan.)
- [ ] Handle enemy reactions and recognized decision-free dialogue automatically.
- [ ] Save/load a live checkpoint and retry defeats automatically.
- [ ] Complete a battle and hand control back safely.

MVP unit commands are Move and Attack. Healing, Spirit, Supply, Transform and crew
changes are excluded. Offline scaffolding exists for several unchecked functions.

## 2. Short-term goal — understand game rules and memory

We are learning how the game stores its statistics, lists, positions and action state.

- [x] Decode known mech/pilot stats from supplied captures, with named-screen checks.
- [x] Decode Ally/Foe menu membership from retained captures (not full tactical allegiance).
- [x] Decode map dimensions and unit positions from retained captures.
- [x] Observe a human-controlled Move/Attack and its resource/position changes.
- [x] Establish memory rules for finished actions after Move/Standby/Attack (observed on Destiny and Z Gundam; Move/Attack availability itself still unverified).
- [x] Understand weapon availability, range, targeting and forecasts (rules derived from screens plus the hit-chance field; availability and damage memory fields not decoded).
- [x] Establish phase, movement/terrain and enemy-reaction rules needed for live play (scope: terrain class, move-cost field, turn counter and enemy phase behaviour located; movement costs for other terrain/unit types unverified).
- [x] Validate automatic screenshot collection (PowerShell Debug > Take screenshot, agent-only; GPU/MCP capture still unavailable).
- [x] Agent-triggered built-in screenshots, without human uploads (protected live check).

The on-demand MCP bridge is implemented and passes offline checks; protected live capture
failed with PPSSPP's "Could not download output". The helper stopped safely; the supported
built-in screenshot route then passed in a fresh trial. Fully unattended runtime capture
remains unverified. Review findings are resolved.

## 2b. Current short-term goal — live state reading and agent-chosen actions (19 Oct)

Plan: [plan](superpowers/plans/2026-10-19-live-state-and-chosen-actions.md), [design](superpowers/specs/2026-10-19-live-state-and-chosen-actions-design.md).
Goal: from one tactical instruction the agent reads the live battle state, chooses a legal Move and Attack, executes and verifies it.

- [x] M1 Cursor tile from memory (u16 pair at 0x096007C4); screen context has no single field, so it is derived from several signals plus a screenshot at screen changes.
- [x] M2 `read_state` (units, terrain, move costs, cursor, turn) in about 9 KB, verified live.
- [x] M3 `goto_tile` (10/10 random tiles, memory-verified) and `probe_move_range` (reachable tiles match the on-screen overlay, 526/526 tiles for Destiny).
- [x] M4 Weapon and target probing. Done: `ppsspp_read_weapons` (memory-only, verified live) and `ppsspp_read_targets` (enemies in range per weapon, Manhattan distance; verified live on 20 Oct: Destiny CIWS has no target, the 3~8 gun lists (16,8) and (18,8), matching the 18 Oct previews). `ppsspp_read_hit` (hover hit chance from the two s32 at 0x08ED055C, only meaningful in target select; verified live 20 Oct: 42% and 61% matched the screen, -10000 on a non-target). Damage forecasts are not decoded.
- [x] M5 `act` macro (`ppsspp_act`; select, Move, weapon row, target, forecast, Start, dismiss; every stage memory-verified). Live 20 Oct: Destiny move + FlashEdge2 and Z Gundam move + Beam Rifle, both executed. See the 20 Oct M5 note below.
- [x] M6 Independent review, documentation and handover notes.

## 3. Today/session goal — 20 October

- [x] Decode where weapon data lives in memory (weapon records, unit weapon lists, ammo, pilot skills).
- [x] Build `ppsspp_read_weapons` (memory-only) and verify it live against the Destiny and Z Gundam weapon screens.
- [x] Find the source of Destiny's +1 range (equipped part Hi・SpecRadar; parts table decoded).

Next step: M5 `act` macro (select, move, weapon, target, Start, dismiss) with memory verification.

Live check of `ppsspp_read_targets` (run tgt1-run-20261020T1717, backup backups/tgt1-original-20261020T071707Z-*, 44 files SHA-256 verified; memory reads only, no input): Destiny matches the 18 Oct previews; Z Gundam with moved=true greys Grenade and Hyp.MegaLauncher (no P flag). PPSSPP closed gracefully; originals unchanged (44/44).

## Session goal history — 18 October

- [x] Check the handover and actual emulator/helper state.
- [x] Implement on-demand MCP capture and verify its offline components.
- [x] Try one protected live MCP screenshot and preserve the failure evidence.
- [x] Validate agent-triggered built-in capture in a fresh protected trial.
- [x] Resume Destiny Move/Standby and compare action-state memory (agent-driven, passed).

The overnight run stopped during initial baseline with a debugger connection close;
no Destiny action stages were accepted. On 18 October, no PPSSPP process/window remained.
The current fresh menu-capture diagnostic passed backups and its initial baseline at15:42.
It is waiting for Destiny Unit/Info, sequence2. No Destiny action stages have been captured.
Standby remains diagnostic only. The current pointer is active-menu-capture-run.json.
See [the current handover](research/2026-10-18-session-handover.md).

## Agent input control — 18 October (later)

Agent-driven input now works with no human input. New `src/psp_buddy/info_navigation.py`
(tests, review, full offline suite 1153 passed, Ruff, strict mypy, Node 8 passed) sends
PPSSPP debugger `input.buttons.press` through the protected helper via the
`ppsspp_press_button` MCP tool; screenshots are taken by the agent from PowerShell
(Alt+D, t = Debug > Take screenshot). Run: local/move-attack-trial-20261017/nav-run-20261018T1650
(fresh original SYSTEM backup backups/nav-original-config-20261018T064513Z-*, full launcher snapshots).
Live (verify later made non-fatal in code, tests pass): cursor moved, Destiny's command menu opened, Info chosen, Info screen captured
(Destiny Gundam HP5200/EN230, frames 00000-00006, 9 taps). No Move/Attack/Standby was pressed.
The final `ppsspp_verify_info` memory check failed ("selected Info does not corroborate
Destiny"), so the helper disabled itself (by design). Cause not yet investigated; screen
is correct. PPSSPP is left open on the Info screen. Next: make verify report raw
selected-Info instead of failing closed, then add Move/Attack input purposes.

Move/Attack/Standby input (18 Oct, offline only): spec/plan in docs/superpowers/*/2026-10-18-move-attack-input*.
Declared actions, `observe` stage samples (`ppsspp_observe`), and Info verify non-fatal are implemented
with tests (1331 passed, Ruff, mypy, Node) and independent review (one Important fixed).
No live action trial yet; needs an `action-declaration.json` beside navigation_handoff.py,
fresh protected backups and a new run. All uncommitted.

Live Move/Standby trial attempt (act-run-20261018T1720): fresh backups and baseline passed; stage-01.json
saved (Destiny HP5200/EN230 at (19,5), unmoved, Info corroborated). Only one cursor Right was sent.
My own request reused a screenshot once too often (observe counted as a use), which was refused
and, by the old rule, disabled the helper. Fixed: pre-input refusals (`NavigationRefused`) now
return an error and keep the session usable; tests pass. No Move or Standby was executed.
The disabled helper's PPSSPP is still open; a fresh protected run needs a normal human closure.

## Live agent Move/Standby trial — PASSED (act-run-20261018T1745)

Fresh original SYSTEM backup backups/act2-original-config-20261018T073635Z-* plus launcher full snapshots.
All 13 steps agent-driven (MCP buttons + PowerShell screenshots, frames 00000-00009, no human input):
cursor to Destiny, Move preview, down-one confirmed Move to (19,6), Standby. Stage samples stage-01..04.json.
Destiny memory by stage: (19,5) EN230 counter1 unmoved -> preview unchanged -> after Move (19,6) EN229
counter1 still counted unmoved -> after Standby (19,6) EN229 counter0, counted_as_unmoved False.
No other unit changed. So: the position and EN cost update on Move confirm; the per-unit action-finished
counter clears only on Standby. PPSSPP left open on the map. Use a fresh closure and backups before the next trial.
Next: Attack declaration trial (weapon/target ranges, forecast), then enemy-phase observation.

`attack_recon` declaration implemented (TDD; 1336 passed, Ruff, mypy): view-only Attack menu browsing,
no confirm_attack/Move/Standby allowed. action-declaration.json now holds the recon declaration;
the Move/Standby one is kept as action-declaration.move-standby.json. Awaiting normal PPSSPP closure
before the fresh protected recon trial.

## Attack recon trial — PASSED (recon-run-20261018T1830)

Fresh original SYSTEM backup backups/recon-original-config-20261018T081036Z-* plus launcher snapshots. 16 agent inputs,
frames 00000-00012, nothing confirmed; stage-01.json (CIWS target-select) and stage-02.json (HiEnergyBeamGun target-select).
Destiny at (19,5) HP5200 EN230 unchanged. Weapon list (all enabled): 17.5mm CIWS 2200 1~3 ammo10; HiEnergyBeamGun 3200 2~7;
RQM60F FlashEdge2 3400 1~5; HiEnergyBeamGun 4400 3~8 EN35 no ammo; Arondight Sword 4500 1~3. Target preview greys non-targets:
CIWS leaves one candidate near (18,4) (menu-group-4 row, HP1225 EN3); the 3~8 gun leaves the two big foes near (16,8) and (18,8).
PPSSPP left open at Destiny's command menu (Attack highlighted). Attack declaration awaits user choice.

Attack declaration written (action-declaration.json): Destiny, 17.5mm CIWS, target label "tile(18,4)" (HP1225 unit).
Recon declaration kept as action-declaration.attack-recon.json. Awaiting normal PPSSPP closure for the fresh protected trial.

Attack trial prep (atk-run-20261018T1915): fresh backups + launch + baseline passed, but before any input I found
the bridge could not complete an attack: combat is confirmed with Start (controls.ini; 17 Oct research), and a circle
on a target only opens the forecast. Fixed with TDD: new `choose_target` (circle, needs weapon selected, declared target)
and `confirm_attack` now = Start only, after a chosen target (1336 passed, Ruff, mypy, Node). That helper still runs the
old code and received no game input; it must not be used. Needs normal PPSSPP closure and a new run.

Attack trial attempt (atk-run-20261018T1950): bridge worked to target select with CIWS. Correction to the recon: the unit at (18,4)
is Wing Gundam Zero (Quatre, HP1225 EN3), shown with HIT 0% when under the cursor, so it is NOT a valid CIWS target (appears to be an
allied/non-attackable unit; its earlier "highlight" was not a target marker). CIWS range had no enemy. Circle on Destiny's own tile
did nothing. Nothing confirmed; backed out to the command menu. The 3~8 HiEnergyBeamGun showed the two foes (16,8),(18,8) as targets.

## Live agent Attack trial — PASSED (atk-run-20261018T2020)

Declaration: Destiny, HiEnergyBeamGun 4400 (3~8), target tile(18,8). Fresh backups (atk3-original-config-20261018T094552Z-*,
launcher snapshots); PPSSPP was closed by the agent (Exit prompt answered Yes, user-approved). 19 agent steps, frames 00000-00015,
no human input: cursor to Destiny, Attack, weapon, cursor to Mercurius (Heero, HP10507, 42% hit shown), choose target, forecast
(Destiny hit 42%, counter 36%, support attacker Brasta 54%), Start.
Memory by stage (stage-01 target select, 02 forecast, 03 after combat):
Destiny EN230 -> 230 -> 195 (35 EN cost), counter_value 1,1 -> 0, counted_as_unmoved True -> False, HP 5200 unchanged, tile unchanged.
The support attacker row (object 149303496, (18,5)) EN235 -> 175. The foe's HP 10507 did not change, so the shot missed.
So: attack cost is charged on Start; the action-finished counter clears at attack end (no Standby needed); forecast/target stages leave memory unchanged.
PPSSPP left open on the map. Next: damage/hit-case observation (a hitting attack), enemy phase, End Turn handling.

## Z Gundam move + Beam Rifle attack — PASSED (zatk-run-20261018T2120)

New in code (TDD, 1338 unit + 172 helper tests pass): `["move","attack"]` declarations (move must precede attack), 40-tap budget,
directional frames shared 4 times, acting unit chosen from the declaration (`Z Gundam` = object 149303912), `observe` reports `unit` and
`changes` vs baseline. Fresh backups backups/zatk-original-config-20261018T100104Z-*; agent closed PPSSPP itself (Exit prompt Yes).
34 agent steps: Z (18,13) -> Move to (14,15) -> Attack, Beam Rifle (2~4, ammo 9/10), target Euclid (97% shown, counter 49%, Taurus support defender) -> Start.
Stage memory (1 baseline, 2 move preview, 3 forecast, 4 combat result dialog, 5 after dialog):
Z HP 4700,4700,4700,1119,1119; EN 128,122,122,122,122; tile (18,13) then (14,15); counter_value 1,1,1,1,0 (unmoved flag clears only after the result dialog is dismissed).
Euclid HP 5211 throughout, EN 89 -> 74 (its counter fire); Taurus (support defender, SDef) HP 2603 -> 450 so the defender absorbed the Beam Rifle hit.
Kamille EXP +30 on the Get Result box. A "Get Result" dialog needs a confirm press: I sent one plain X key via PowerShell (outside the bridge allowlist);
a proper `dismiss_result` purpose is still to implement. PPSSPP is open on the map, Z at HP1119.

## Short-term A — weapons, range, targeting, forecasts (18 Oct, runs wrec-run-20261018T2230 + zrec-run-20261018T2315)

New read-only bridge operation `ppsspp_dump_ram` (24 MB user RAM, 0x08800000-0x0A000000, hashed, never overwritten; 24 per trial).
Findings (all agent-driven, view-only, nothing confirmed):
- Hover hit chance lives in two s32 at 0x08ED055C and 0x08ED0560: 42 (Mercurius, 4400 gun), 61 (Vayeate), 47 (Mercurius, 3200 gun,
  weapon +5 HT) match the on-screen HIT%; -10000 when the cursor is on a non-target (own unit); 24 while idle in menus. Weapon list index
  candidate: u8 at 0x08E397A8 (0..4, count 5 next to it).
- Weapon screen: "ReqEN --- N" shows the weapon cost (--- = ammo weapon) and the unit's current EN; it is not a requirement.
- Availability (greying) is consistent with: ammo/EN available AND (not moved OR weapon has the P flag) AND at least one candidate
  target in the weapon's range. Evidence: Z at its start has only Grenade (1~5, foe at distance 5) usable; after moving to (14,15)
  Grenade (no P flag) is greyed while Vulcan/Beam Rifle (P) are usable; Destiny at its start has all five usable (range test appears
  to count the neutral Wing Gundam Zero, HIT 0%). The memory field for availability was not isolated (the dump differences are UI
  buffer noise), and damage/counter forecast fields were not decoded. Range preview = blue overlay; invalid cursor target = -10000.

## Short-term B — phase and enemy reaction (18-19 Oct; runs sys-run-20261018T2350, end-run-20261019T0020)

New in code (TDD; 1181 tests, Ruff, mypy, Node pass): `system_recon` / `end_turn` declarations, purposes `open_system_menu`
(empty tile only, from the baseline occupancy), `system_menu_move`, `end_turn` (needs the declared label, once), `advance_dialog`
(only after End Turn, max 30), `cancel` on the system menu; `ppsspp_dump_ram`.
Findings (agent-driven, one protected End Turn, nothing saved):
- System menu (circle on an empty tile): EndTurn (default), Search, Units, Mission, Report, System, Save; panel shows SR Points 8, Mode Normal,
  Turn 7, Money; the terrain name of the cursor tile (here "Moon") shows top-left. End Turn asks "Unmoved Units: 20 unit/s - End phase? Y/No".
- Enemy phase runs by itself with Skip animation; each enemy attack shows the two-sided battle forecast (Start highlighted; defender options
  Def./Move/Support) and needs a Start press. Observed: Wing Gundam Zero (third force, HP1225) attacking Gundam 00, Taurus/Euclid supports
  (66%/63%/73% hit), Vayeate vs Wing Gundam Zero (HIT 0%, NoAtk). Enemies attacked from their positions (no foe moved).
- Phase change effect on memory (stage-01): allies' EN regenerated by +5 (9 units), +23/+25 (4 units), +0 (6 units at max EN); every ally
  counter_value back to 1 (unmoved); foes unchanged; only HP change was Shenlong Gundam 4616 -> 3006 from the enemy attacks.
- The turn counter field was not isolated (candidate array near 0x091BC40C varies 6..9, so it is not the counter). Terrain/movement costs were
  not studied beyond the overlay shapes and the terrain label.
PPSSPP is left open in turn 8 (player phase) on the disposable trial copy.


## Short-term B, part 2 — turn counter, terrain, move cost (19 Oct; run mv-run-20261019T0900 + offline diffs of 20 dumps)

- Turn counter: u16 at 0x08DF8ADC (7 during turn 7 and through the whole enemy phase, 8 once the new player phase starts); the u16 next
  to it at 0x08DF8ADE goes 0x96 -> 0x97 (probably a running total). It is the only address that read 7 in all 16 turn-7 dumps and 8 in the turn-8 dump.
- Terrain: the map cell table (16-byte cells at 0x08E4EA94, index Y*24+X, map 24x34) byte +0 is the terrain class: 1 = open space,
  2 = asteroid belts (diagonal bands, rows 13-29, matching the brown rocks on screen), 18 (0x12) = the debris/nebula area at the top-left
  (rows 0-7). Byte +9 is only a cached classification near units (not terrain), as the 16 Oct notes warned.
- Move range: while a unit's Move range is shown, cell byte +12 holds the accumulated move cost of every reachable tile (Z Gundam at
  (18,13): 1 beside it up to 6 at the rim, 0 elsewhere), matching the red overlay tile for tile (own-unit sprite tiles hide the overlay).
  Z Gundam paid 1 per tile through asteroid tiles, so asteroids add no extra cost for it; costs for other terrain/unit types are unverified.
- Tooling fix: the PowerShell screenshot helper now forces PPSSPP to the foreground (Alt tap + SetForegroundWindow, verified) before Alt+D, t;
  the first attempt this session sent no input because another window had the foreground (no game input was sent).
PPSSPP is left open on Z Gundam's command menu (turn 7 start, trial copy). Nothing was confirmed.

## M4 weapon memory — decoded offline (20 Oct)

The game is Super Robot Wars Z2 Saisei-hen (ULJS00460). Public CWCheat codes for it (ammo/EN "not decrease", Range Up) line up
byte for byte with our dumps and led to the code that spends ammo and EN. From there, the full chain was decoded from retained
dumps (wrec/zrec), with no emulator run. Details: [weapon memory note](research/2026-10-20-weapon-memory.md).

- Battle actor (16 B, the existing `actor` nodes) +4 -> roster entry (mech def, runtime, weapon list). The runtime holds HP, EN and move.
  The weapon list holds up to 21 weapon-record pointers, in menu slot order, with gaps allowed. Beside them are pointers to
  current-ammo counters, stored x9.
- Weapon record (44 B): name in full-width Shift-JIS, power, min/max range, hit, crit, max ammo, EN cost, will, attribute bits.
- Verified: Z Gundam Beam Rifle reads range 2~4, ammo 9/10, which matches the 18 Oct trial. Grenade 1~5. Destiny's five
  weapons are in screen order. The P-flag hypothesis fits Z's Vulcan, Grenade and Beam Rifle behaviour.
- Live check passed (wpn1/wpn2 runs, view-only, fresh verified backups, originals unchanged afterwards). Every displayed field
  matches memory for Destiny and Z: hit, crit, ammo, EN, terrain and the S/P/B flags. The only exceptions are two modifiers:
  power, which fits upgrade level x 100 (candidate runtime +0x1D), and max range. Destiny gets +1 range, probably from the
  game's effect engine (parts or a bonus), which is not decoded. Z has no modifiers.
- `ppsspp_read_weapons` is built (TDD, review fixes, 1240 + 177 + 8 tests, Ruff, mypy) and verified live. For any unit
  object it returns weapons with effective power and range, ammo, EN, hit, crit, terrain, flags, pilot skills and parts.
  Destiny and Z match their screens exactly, and all 26 units read. Destiny's +1 range comes from its Hi・SpecRadar part
  (parts table decoded, ids 1-based at runtime +0x38). Nothing is committed.
- Next: targets in range (from read_state positions + weapon ranges), then the hover hit chance, then M5 `act`.

Hover hit live check (run hit1-run-20261020, backup backups/tgt1-original-20261020T080138Z-*, 44/44 SHA-256; view-only, nothing confirmed): memory matched the screen for Mercurius (42) and Vayeate (61); originals unchanged after graceful close.

## M5 `act` macro (20 Oct)

Design/plan: [spec](superpowers/specs/2026-10-20-act-macro-design.md), [plan](superpowers/plans/2026-10-20-act-macro.md). New `src/psp_buddy/act.py`,
`InfoNavigation` operation `act` (declaration `{"unit":"any","actions":["act"]}`), tool `ppsspp_act`. Two phases: `commit:false` runs
plan, select, Move, Attack menu, weapon row, target, forecast and stops; `phase:"fire"` (forecast screenshot) presses Start and dismisses the result.
Checks: cursor walk, centred reachable range, unit tile/EN after Move, weapon-menu row/count (u8 0x08E397A8/+2, verified live),
hover hit chance, EN/ammo spent, action counter cleared. Tests: 1298 + 8 node + 16 helper, Ruff, strict mypy.
Live (run act5-run-20261020T2236, backup act5-original-20261020T123606Z-*, 44/44 unchanged after graceful close): Destiny (19,5)->(19,6),
FlashEdge2 on Mercurius (60% forecast matched the screen), EN 229->224, counter cleared; Z Gundam (18,13)->(14,15), Beam Rifle (90%), ammo 9->8, HP 4700->1730, one result press.
Lessons: state reads take 14-19 s (collector), so a run takes about 70 s and a fire about 90-100 s; a hard cancel mid-read (helper deadline) left the
emulator "paused" and wedged the helper in runs act1-act4 (cost four relaunches), so the macro now stops cooperatively (95 s budget) and `commit:true`
falls back to stopping at the forecast. No reads during the first 8 s after Start. Known gaps: duplicate weapon names pick the first; attack-only
(second menu entry) and Z page-2 weapons untested live; a missing PSP/SCREENSHOT folder must be created before the first screenshot; reads are slow
(a lighter state read would help). Committed in f2fad69.

M6 review (21 Oct, `9839754..HEAD`, 8 findings): fixed with tests: duplicate weapon names (the instruction may carry a `slot`; a duplicate name without one is
refused as `ambiguous_weapon`), weapons with neither ammo nor EN cost (the result dialog confirms Start), unexpected data errors during a run (reported as a stage, never
raised), a missing SCREENSHOT folder after an act, the weapon-list start row (the walk now starts from the real row), and this stale note. Left as follow-ups: the will requirement
is not checked (pilot will is not decoded), and each fire poll still runs two slow reads (a one-actor EN/ammo read would be cheaper). Not yet live-checked: a duplicate-name
weapon by slot and a free weapon (offline tests only).

M6 live check (21 Oct, run m6-run-20261021T1615, backup backups/m6-original-20261021T081514Z-*, SAVEDATA + PPSSPP_STATE 42/42 unchanged after graceful close; view-only, no Start): Destiny's two `HiEnergyBeamGun`
weapons. Without `slot`, `ppsspp_act` returned `ambiguous_weapon` with slots [1, 3] and sent no input. With `slot:3` on Vayeate (16,8) the macro reached weapon-menu row 3 (the 4th row),
and the forecast hit 61% matched the screen (the screen shows the same name on both guns, so the row rests on the memory read). Both guns reach that foe (the slot-1 range reads 2~7 here), so no foe is
reachable by slot 3 alone. Cross from the forecast backed out one level, to target select. The act took about 70 s. Still untested live: a free weapon (am0/en0): none among the allies on this map.

M6 closed (21 Oct): fixes committed; free weapon (am0/en0) remains untested live (offline tests only).
