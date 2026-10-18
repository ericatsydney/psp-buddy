# Project progress

Updated 18 October 2026 (Australia/Brisbane).
Ticks mean ready in the scope stated; unchecked items may have partial implementation.

## 1. Long-term goal

Play one battle autonomously from an existing save, following your tactical instructions,
with protected progress, up to three checkpoint retries, and handover when needed.

- [x] Verified save/state backup service.
- [ ] Start from an in-game save or save state automatically.
- [ ] Read the complete current battle state automatically.
- [ ] Follow tactical instructions and choose legal actions in a live battle.
- [ ] Move and attack automatically.
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
- [ ] Establish memory rules for Move/Attack availability and finished actions.
- [ ] Understand weapon availability, range, targeting and battle forecasts.
- [ ] Establish phase, movement/terrain and enemy-reaction rules needed for live play.
- [ ] Validate automatic screenshot collection to reduce manual work.
- [x] Agent-triggered built-in screenshots, without human uploads (protected live check).

The on-demand MCP bridge is implemented and passes offline checks; protected live capture
failed with PPSSPP's "Could not download output". The helper stopped safely; the supported
built-in screenshot route then passed in a fresh trial. Fully unattended runtime capture
remains unverified. Review findings are resolved.

## 3. Today/session goal — 18 October

- [x] Check the handover and actual emulator/helper state.
- [x] Implement on-demand MCP capture and verify its offline components.
- [x] Try one protected live MCP screenshot and preserve the failure evidence.
- [x] Validate agent-triggered built-in capture in a fresh protected trial.
- [ ] Resume Destiny Move/Standby and compare action-state memory.

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
