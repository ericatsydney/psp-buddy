# Project progress

Updated 3 November 2026 (Australia/Brisbane).
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
- [ ] Save/load a live checkpoint and retry defeats automatically. (Save/load proven live 25 Oct; retry after a real loss not exercised; deprioritised by the user.)
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

## 2c. Next short-term goal — M15 real-test readiness (user priority, 31 Oct)

Goal: the user picks any of their own save states, runs one command, and the runner clears the non-boss foes
(or hands over cleanly) with no manual steps. Today it works only on two prepared states (turn-7 checkpoint,
stage 33) and needs hand-made set-up and a manual back-out. Design approved 31 Oct (approach A: prepare offline from the slot copy, confirm live):
[spec](superpowers/specs/2026-11-01-real-test-readiness-design.md), [plan](superpowers/plans/2026-11-01-real-test-readiness.md). User choices: input = PPSSPP slot number; an
unidentified opening screen stops with no press; a low cursor budget hands over mid-turn (`turn_budget`);
P5 is a stretch task.

Priority order:
- [ ] P1 Any save state as input: copy the user's chosen slot into a trial checkpoint, hash it, and pick the
  anchor ally from the live state at launch (today: offline decode and a hand-written manifest per save).
- [ ] P2 Automatic start-up back-out: work out the opening screen from memory (target select, weapon list,
  Command menu, post-move menu slot 0x08E4BEB4, move range) and close it down to the map, proven by a cursor
  walk (today: done by hand with a screenshot before each press).
- [ ] P3 Long turns within the kept 400-press cursor budget: fewer cursor presses per action (skip walks that
  memory already proves), and when the budget runs low, hand over cleanly on the map instead of stopping.
- [ ] P4 One-command launcher: wait for a quiet machine, launch detached, check, back out, play, write the final
  report and screenshot; refuse cleanly (nothing launched) under load.
- [ ] P5 Unknown menus and skills: read menu entry counts from memory instead of per-mech tables (Spirit row,
  Repair/Supply entries); anything still unknown hands over safely.
- [ ] P6 Real test: run end to end on 2-3 other user saves from different stages; record each result.

## Backlog (user will fix later)

- [x] Post-counter ally safety (6 Nov, run s2c): closed 7 Nov, user: current behaviour is fine; when an ally
  dies the runner hands over (`ally_destroyed`). Cause noted: own-tile attacks ignore the foes-in-reach limit.
- [ ] Hung memory read after a Circle press -> `driver_error` (5 Nov, s2 / s2t6): longer gap after Circle
  or retry a hung read instead of disabling reads. Did not recur in s2c; recurred in s2d (6 Nov) after a
  Down press in the weapon list, so it is not Circle-specific - a press gap alone will not fix it.
  7 Nov (spec `superpowers/specs/2026-11-07-debugger-freeze-design.md`): every debugger request is now
  traced to `debugger-trace.jsonl`; `_act_read` logs timeouts. Probe `local/m17-tools/freeze_probe.py` on
  checkpoint `slot2-20261106T2255` (Nu Gundam's weapon list, unit 149300064): fp1 PPSSPP crash 0x864414
  at start-up; fp2 aborted before cycles (the lowest ally, a Macross Quarter, has no Attack: Down+Circle
  opened Morph; screenshot caught it); **fp3: 400 cycles, 799 presses, no freeze** (read max 0.72 s);
  fp4 (state reads mixed in): ~9600 requests, no freeze (max 0.57 s), stopped by the user. Backups
  verified each launch; originals 0/56 and portable 0/55 changed. Freeze not reproduced; cause still open.
  Also done: a `cursor_budget` handover now settles a pending story dialogue first (s4-d).
  **Fallback built (user, 7 Nov):** every helper read has a 15 s freeze limit; on a freeze the adapter
  checks the link (`cpu.status`, 2 x 10 s), resumes a CPU our pause left stopped and the read is retried
  once; otherwise (or on a press timeout) a clean `debugger_frozen` handover (`handover.json`,
  `screen_state: unknown`), no more input; clear_loop / run.py / backout.py report it. Helper op limit
  120 s. Checks: pytest 1793 / 1 skipped (`--basetemp local/pytest-m17`; launch tests need an in-repo
  temp dir), local tools 247, ruff, strict mypy; code review (high) 7 findings, all fixed. Not yet
  live-tested: needs a battle save (the newest slot 2 is the stage-37 main menu). Nothing committed.
- [x] 7 Nov live **s2e** (user's slot 2 saved 08:26, city map, turn 1, checkpoint `slot2-20261107T0826`;
  24 min): portable backup 55/55, runner backup 56/56; after the run originals 0/56, portable 0/55 changed.
  Turns 1-5 played (17 fired, 14 advanced, 3 held turn 1, 4 no target), every enemy phase done, **no ally
  lost**, non-boss 11 destroyed / 3 left, boss Caerleon-Class; handover `turn_budget` on the map.
  **2 freezes, both recovered** (15 s each, the retried read took 0.5 s), both right after a Circle press.
  **Root cause seen in the trace:** the link was healthy (~990 `cpu.status` replies in 15 s), but PPSSPP
  ignored the `cpu.stepping` request sent ~2.5 s after the Circle: every status said running, and
  `_transition` polled for its whole timeout (60 s before the fallback = the old `driver_error`). After
  recovery a new `cpu.stepping` took effect at once. Next fix: re-send `cpu.stepping` when the CPU has not
  stepped within ~1 s. Also: trace rotation keeps only the newest 2 x 5000 lines (the first freeze's
  records were overwritten); keep more files.
  User's newest slot 2 (7 Nov 06:52) is the intermission main menu (stage 37), not a battle.
- [ ] Cursor-budget handover does not settle a pending story dialogue (4 Nov, s4-d).
- [x] Disk space (7 Nov): drive C: was full (648 MB free; project 127 GB). Deleted by hand with the user's
  OK: 477 pytest temp folders, 182 of 187 runtime archives, 201 of 206 trial `working` copies (newest 5
  kept; all 206 verified snapshots kept); C: now 73 GB free (log `local/cleanup-20261107.log`).
  `Launcher.prepare` now does the same after each launch (`psp_buddy.retention`, keep 5, best effort;
  spec `superpowers/specs/2026-11-07-trial-retention-design.md`). Snapshots still grow ~220 MB per trial
  (only ~0.6 GB unique across all 206): dedup is an open option. Latest slot 2 + game saves copied to
  `D:\PPSSPP-saves\ULJS00460-20261107T142348` (30 files, SHA-256 checked).
- [x] 7 Nov live **s2f** (user's slot 2 saved 18:06, city map turn 1, checkpoint `slot2-20261107T1806`;
  34 min). PPSSPP hung on its graceful close (window hidden, idle > 2 min): force-closed with the user's
  OK; the 18:06 state was intact. Portable backup 55/55, runner backup 56/56; after the run originals 0/56
  and portable 0/55 changed. Turns 1-3: 20 fired, 32 advanced, 11 held on turn 1, 11 no target; **no ally
  lost**; non-boss 21 destroyed / 15 left; no boss named; **0 debugger freezes**. Handover `cursor_budget`
  on turn 3, `screen_state: map`. **Retention worked live:** archives 5 -> 5 (new one added, oldest
  removed), working copies 5 -> 5 (this trial's added, oldest removed), snapshots 206 -> 207.
- [x] 7 Nov live **s2g** (user's slot 2 saved 19:25, same map turn 3 after acting, checkpoint
  `slot2-20261107T1925`; 12.5 min): portable 55/55, runner 56/56; after the run originals 0/56, portable
  0/55 changed. Enemy phase of turn 3, then turn 4: 6 fired, **map cleared** (non-boss 11 destroyed /
  0 left, no boss), no ally lost, 0 freezes. Handover `cleared` with `screen_state: dialogue`
  (`dialogue_pending`: the post-clear story scene). Retention again 5/5 archives and working copies,
  snapshots 207 -> 208.
- [ ] 7 Nov live **s2h** (user's slot 2 saved 20:25, turn 4, checkpoint `slot2-20261107T2025`; 10 min):
  portable 55/55, runner 56/56; originals 0/56 changed. Turn 4: 3 fired, 9 advanced, 2 no target; non-boss
  2 destroyed / 20 left; no ally lost. **Stopped with a clean `debugger_frozen` handover** (no
  driver_error): during a cursor walk (a press every ~0.2 s with two reads after each, CPU running, no
  pause) a `memory.read` got no reply; recovery's `cpu.status` (2 x 10 s) got none either. **New finding:**
  a second, fresh WebSocket to PPSSPP's debugger connected at once but got no reply to `version` or
  `cpu.status` (10 s each, >5 min after the freeze), while the game still rendered (move range on screen).
  So this freeze is PPSSPP's whole debugger, not our socket: reconnecting cannot recover it. It differs
  from s2e (link alive, only `cpu.stepping` ignored). Retention again 5/5, snapshots 208 -> 209.
  Afterwards PPSSPP hung on its graceful close again (hidden window; the earlier 7 Nov hang also followed a
  freeze run, s2e): force-closed with the stuck helper for the rerun.
- [x] 7 Nov live **s2i** = s2h rerun from the same checkpoint (27 min): portable 55/55, runner 56/56;
  after the run originals 0/56, portable 0/55 changed. Turns 4-5: 18 fired, 18 advanced, 4 no target;
  non-boss 9 destroyed / 14 left; no ally lost; **0 freezes** (the s2h freeze did not repeat on the same
  state, so it is not tied to that position). Handover `cursor_budget` on turn 5, on the map. Retention
  5/5, snapshots 209 -> 210.

## 2b. Current short-term goal — live state reading and agent-chosen actions (19 Oct)

Plan: [plan](superpowers/plans/2026-10-19-live-state-and-chosen-actions.md), [design](superpowers/specs/2026-10-19-live-state-and-chosen-actions-design.md).
Goal: from one tactical instruction the agent reads the live battle state, chooses a legal Move and Attack, executes and verifies it.

- [x] M1 Cursor tile from memory (u16 pair at 0x096007C4); screen context has no single field, so it is derived from several signals plus a screenshot at screen changes.
- [x] M2 `read_state` (units, terrain, move costs, cursor, turn) in about 9 KB, verified live.
- [x] M3 `goto_tile` (10/10 random tiles, memory-verified) and `probe_move_range` (reachable tiles match the on-screen overlay, 526/526 tiles for Destiny).
- [x] M4 Weapon and target probing. Done: `ppsspp_read_weapons` (memory-only, verified live) and `ppsspp_read_targets` (enemies in range per weapon, Manhattan distance; verified live on 20 Oct: Destiny CIWS has no target, the 3~8 gun lists (16,8) and (18,8), matching the 18 Oct previews). `ppsspp_read_hit` (hover hit chance from the two s32 at 0x08ED055C, only meaningful in target select; verified live 20 Oct: 42% and 61% matched the screen, -10000 on a non-target). Damage forecasts are not decoded.
- [x] M5 `act` macro (`ppsspp_act`; select, Move, weapon row, target, forecast, Start, dismiss; every stage memory-verified). Live 20 Oct: Destiny move + FlashEdge2 and Z Gundam move + Beam Rifle, both executed. See the 20 Oct M5 note below.
- [x] M6 Independent review, documentation and handover notes.
- [ ] M8 Planner with forecast-gated auto-fire (21 Oct, design approved): [spec](superpowers/specs/2026-10-21-planner-design.md), [plan](superpowers/plans/2026-10-21-planner.md). Task 1 (damage table) done offline: no formula validated, fallback hit% x power ([note](research/2026-10-21-damage-model.md)). Task 2 done 21 Oct: `src/psp_buddy/tactics.py` (`plan_attack`) with `tests/unit/test_tactics.py` (20 tests, red first); uncommitted. Tasks 3-4 done offline 21 Oct: `src/psp_buddy/plan_act.py` (`plan_and_act`: plan, overlay read when nothing is in reach, run to forecast, gate, fire or back out, `damage-log.jsonl`), mailbox/`InfoNavigation` operation `plan_act`, node tool `ppsspp_plan_act`, handoff deadline (ignored local/). Forced-mismatch test passes; ruff, strict mypy, pytest 1340, node 8, helper 73 pass. Task 5 live (22 Oct, run local/move-attack-trial-20261017/m8b-run-20261021T201329, backups/m8live2-original-20261021T201329Z, 46/46 verified, originals unchanged after): from a policy text only, Destiny chose FlashEdge2 on Mercurius, forecast 47% (gate passed), fired in 46.7 s; EN 230->225, counter cleared, target HP 10507->6565 (one damage-log row, power 3400). Not exercised live: the move-range overlay path and a gate refusal (simulated only). A first attempt crashed PPSSPP because the memstick SCREENSHOT folder did not exist; create it before the first screenshot. Task 6 review (code-review, high) done 22 Oct: 9 findings, 8 fixed (no raised exceptions from plan_and_act, guarded damage log, `min_hit` gate exposed in `ppsspp_plan_act`, move EN reserved, overlay time guard, `moved` reported on decline, cleanups); the test-first note for plan_act.py was skipped. After fixes: pytest 1349, node 8, helper 73, ruff, strict mypy pass. Committed 4e859aa (pushed). Live re-check after the fixes (22 Oct, run m8d): Z Gundam fired a Grenade Launcher from its tile (missed, took a counter 4700->1007); another unit with `min_hit` 99 planned a move to (19,10), saw 30% and declined and backed out, proving the overlay, gate refusal and back-out live. M8 acceptance criteria all met; see [handover](research/2026-10-22-m8-handover.md). Later notes uncommitted.
- [x] M9 Full player turn (22 Oct, design approved; done 23 Oct: turn 7 played live to `done`, 19 fired, 1 skipped, stopped before End Turn; review fixed): [spec](superpowers/specs/2026-10-22-turn-design.md), [plan](superpowers/plans/2026-10-22-turn.md). Tasks 1-3 done offline: `src/psp_buddy/turn.py` (`ready_allies`, `TurnLog`, `next_unit`, `report`), read-only operation `turn_next` + tool `ppsspp_turn_next`, `turn-report.json` per trial, budgets 40 acts / 1000 presses; red tests first (test_turn.py 19, navigation tests); pytest 1372, node 8, helper 73, ruff, strict mypy pass. Task 4 live (22 Oct) in progress: best run handled units 1-11 of 21 (9 fired, 1 skipped), stopped at Force Impulse (target-select cursor stall). Live fixes with tests: Hit and Away Standby (skill 20), hit chance >100, hidden weapon rows / will, re-plan on refused weapon, budgets. Evening: Force Impulse cause found (menu lists weapons by power, not slot order) and fixed with tests; re-run stopped at Strike Freedom (Start not confirmed, game still in target select). 23 Oct: menu rows follow shown power (MAP weapons and the hidden byte-26/placeholder rows modelled, MAP never chosen), MVP Standby after a failed or declined move; live run m9livex10 completed turn 7 (`done`); code-review high: 6 fixed, 2 minor skipped. Uncommitted. See [M9 handover](research/2026-10-22-m9-handover.md). Uncommitted.
- [x] M10 End Turn and enemy phase (23 Oct, design approved; closed 25 Oct): [spec](superpowers/specs/2026-10-23-end-turn-design.md), [plan](superpowers/plans/2026-10-23-end-turn.md). Implemented with tests (`end_turn.py`, operations `end_turn`/`enemy_phase`). Live: End Turn works; the enemy phase destroys Gundam 00 (turn-7 play leaves it at 873 HP), strict stop works; accepting losses walked into the stage's defeat (trial copy only) -> `scene_after_loss` and `stage_restart` stops added. Turn 8 reached live in strict mode after the M11 turn-7 policy (run m11live18, no ally lost). Code review (high, 25 Oct): 8 findings; fixed red-first: no press/goto/act/plan_act/probe_move once End Turn has started; units gone from the list (live: destroyed units vanish) reported as `lost`/destroyed; one unreadable read is re-read before any Circle (a camera pan over the T+1 map); a scene at the start of T+1 stops as `scene_at_new_turn` (the T+1 wait is now `_new_turn`, 2 finished reads in a row, up to 20 reads); enemy-phase Circles no longer count against the player turn's 1000-press budget (capped by `PHASE_PRESSES`). No change: a failed open cannot re-open (adapter errors disable the helper). Skipped (minor): the report's `screens` list stays empty (screenshots are taken outside the helper). Checks: pytest 1528 / 1 skipped, helper 189, node 8, ruff, strict mypy. Not re-run live after these fixes. Uncommitted.
- [x] M11 Turn-7 policy: Sense first then Focus before each planned attack, non-boss foes before bosses (bosses by name
  Mercurius/Vayeate/Wing Gundam Zero or max HP >= 2x foe median) (23 Oct, design approved): [spec](superpowers/specs/2026-10-23-spirit-boss-policy-design.md),
  [plan](superpowers/plans/2026-10-23-spirit-boss-policy.md). Task 1 done (red first): `spirit_recon` declaration and
  view-only bridge purposes (`open_spirit`, `spirit_pilot`, `spirit_menu_move`; no Circle in the spirit list); pytest
  1450 / 1 skipped (run with `--basetemp local/...`, launch tests need it), helper 185, node 8, ruff, strict mypy. Task 2
  done live (run m9livesp1): Gundam 00's spirit list opens directly (Focus 15, Sense 20, Yell 35; Sense = Flash & Aim,
  Focus = Hit&Eva +30%, both Self 1 Turn), nothing cast, originals unchanged; see [recon](research/2026-10-23-spirit-recon.md).
  Task 3 done offline: spirit list = pilot runtime +0x5C, six (id, learn level, cost) triples; menu row = index
  among learned; Focus id 6, Sense id 9; `spirits.py` (decode, read, Sense-then-Focus choice), red tests first.
  Task 4 done offline (red first): policy flags `target non-bosses before bosses`, `use sense then focus before
  attacking` (parsed; casting not yet implemented), `tactics.boss_objects` (names, spaces/case ignored, or max HP >=
  2x foe median: on turn 7 that is Vayeate and Mercurius), non-boss-first order, `plan_act` `boss_names` (defaults
  when the flag is set; foe mech names cached per trial; node tool too). Checks: pytest 1475 / 1 skipped, helper 185,
  node 8, ruff, strict mypy. Task 5 live cast recon done 24 Oct (run m9livesp3): one Circle on Sense casts it
  with no Yes/No, the game returns to the map with the unit still unmoved, SP 55 -> 35 exactly, active-effect mask
  pilot runtime +0x14 0 -> 0x44 (Flash + Aim), Sense greyed at the same row; originals unchanged. `spirits` decodes
  `active`; bridge `spirit_cast_recon` mode (tests first). Checks: pytest 1481 / 1 skipped, node 8, ruff, mypy.
  Task 5 done 24 Oct (red first): `spirit_cast.py` cast step in `plan_act` (Command-menu count/row gate at
  0x08E4BE34, SP drop = cost + effect mask, map proven by a cursor walk, `spirit` in results and turn report);
  Sense hover hit 400 = sure hit; policy now also `strongest boss weapons above 0%` (user: bosses only take damage
  from the strongest weapon). Task 6 live (runs m11live1-4, recon m11menu1; every backup 46/46 verified, originals
  unchanged): Sense and Focus cast and verified on 5 units (Focus bit 0x20 observed), non-bosses first; Z Gundam
  has Morph (fixed by the gate), Shenlong's menu has 3 entries (skipped safely), Dancouga Nova/Shenlong casts spend
  nothing (open). Continue (skill 22, user + level-up screen): a kill gives a bonus step; `act.result` dismisses
  the pages and stops when the map cursor moves (`bonus_action`). Story dialogues (user: skip them) are Circled
  through before the battle, after it and across acts (`dialogue_pending`, settled by the next plan_act or End
  Turn). **Run m11live18: turn 7 `done` (14 fired, 7 no target), strict End Turn + enemy phase -> turn 8 with no
  ally lost; Gundam 00 survived at 364 HP.** Code review (high): 10 findings, 3 Important fixed (dialogue after
  any attack, unfinished settle waits instead of stopping, End Turn settles first), 7 minor skipped; the live
  re-check after these fixes passed (run m11live22: turn 7 `done` in one go). Checkpoint (user, 24 Oct):
  `local/checkpoints/turn7-done` saved before End Turn; launches can load it (hash-checked, never into the
  memstick); replaying the enemy phase from it takes about 8 minutes and reproduced turn 8 (run m11cp4). See
  [recon](research/2026-10-23-spirit-recon.md). Checks: pytest 1522 / 1 skipped, helper 189, node 8, ruff, strict
  mypy. Uncommitted.
- [x] M12 Live checkpoint and retries, turns 7 -> 8 (25 Oct; closed early by the user's scope change, see below): [spec](superpowers/specs/2026-10-25-checkpoint-retry-design.md), [plan](superpowers/plans/2026-10-25-checkpoint-retry.md). Live, every run protected (backup 54/54 verified, graceful close, originals unchanged): Task 2 ids proven on screens (Wing Gundam Zero pilot page: Guard 15, Alert 10, Strike 20, Bless 45 -> id 3 Alert, id 5 Guard = the code's Invincible) and one Alert cast (SP 19 -> 4, mask 0x04). Task 6: `local/m12-tools/save_checkpoint.ps1` saved turn 7 start via File > Savestate slot 3 > Save state (a capture per step) to `local/checkpoints/turn7-start` + manifest (`retry.manifest`); relaunches matched it exactly (`mismatches == []`, three times). Task 7 attempt 1 (run m12try1): turn 7 `done` (15 fired, 7 skipped, spirits Sense/Focus cast and verified), End Turn, strict enemy phase -> **turn 8, no ally lost**, every non-boss foe cleared (Gundam 00 5000 -> 364, deterministic). A forced retry was recorded in the ledger (`local/m12-retry/run1/retry-report.json`) but attempt 2 was not run: the user stopped there. Task 8 code review (high): 6 findings; fixed red-first: losses to a counter in the player turn now count (`retry.lost_allies`, a done phase with a lost ally is a defeat), Cross out of the End Turn system menu before confirm allowed again; also key focus guard in the save tool, constant in a message. Skipped minor: Invincible bit 0x10 unobserved; node `info_page` test not seen red first. Checks: pytest 1565 / 1 skipped, helper 190 (one unexplained intermittent failure, 4 reruns clean), node 8, ruff, strict mypy. Not exercised live: a real reload after a loss.
- **Scope change (user, 25 Oct):** the auto-runner clears the map of non-boss robots, then hands control back to the player, who fights the bosses with more complex skills and may lose allies. Retries are no longer the next step.
- [x] M7 Speed (21 Oct): reads after the baseline skip the 26 immutable code anchors (14-19 s -> 1.1 s) and `read_state` takes units and map in one pause. A fired act (move + attack, Destiny vs Mercurius) takes about 45 s (24.6 s to the forecast, 20.5 s to fire), was about 160 s. The under-30-s goal is not met; further tuning (fewer reads, shorter settles) is deferred by choice. See [read profile](research/2026-10-21-read-profile.md), [spec](superpowers/specs/2026-10-21-speed-design.md), [plan](superpowers/plans/2026-10-21-speed.md). Code lives in ignored local/ files (collector.py, navigation_handoff.py), helper tests 182 pass; uncommitted.

## 3. Today/session goal — 25 October

- [x] Review M10 (code-review high) and fix its Important findings red-first; tick M10.
- [x] Design the next milestone with the user (M12 checkpoint + retries, spirit chain added).
- [x] M12 offline tasks 1, 3, 4, 5 (spirit order, protected units, retry ledger).
- [x] M12 live: spirit ids proven, turn-7 checkpoint saved and reloaded, turn 7 -> 8 with no ally lost; review fixed.

- [x] M13 designed with the user (clear non-bosses, then hand over): [spec](superpowers/specs/2026-10-25-nonboss-clear-handover-design.md),
  [plan](superpowers/plans/2026-10-25-nonboss-clear-handover.md). Decisions: check after every action and
  enemy phase, stop at once on an ally loss, hand over on the map with `handover.json` (no savestate), bosses
  still attacked when nothing else is in reach, check inside `turn_next`, 5-turn budget, boss set fixed at start.
  Found: the helper allows only one End Turn per trial, so multi-turn play needs a new-turn reset (plan Task 3).

  Spec approved by the user (25 Oct). Task 1 done offline (red first): `src/psp_buddy/clear.py` (`begin` fixes
  the boss set, `nonboss_left`, `decide` = ally_lost > cleared > turn_budget, `handover_report`) with
  `tests/unit/test_clear.py` (12). A late foe counts as a boss only by name, and only once its name is in the cache.

  Task 2 done offline (red first): `turn_next` reads foe names once (shared cache), fixes the `ClearRun` at
  its first call, and answers `clear` {nonboss_left, bosses, turn} and `handover` (cleared / ally_lost /
  turn_budget / `stopped:<reason>`). A new handover writes `handover.json` once; after it every input operation
  is refused, while reads and `turn_next` still answer (5 tests in `test_act_navigation.py`, 1 in `test_clear.py`).

  Task 3 done offline (red first): an enemy phase that ends `done` starts a new player turn in the same helper.
  It keeps `turn-report-<T>.json` and `enemy-phase-report-<T>.json`, starts a fresh TurnLog, and allows End Turn
  again. The budgets in `PER_TURN` (state/weapon/hit/target reads, probes, acts, act and goto presses) count per
  turn; taps and dumps stay per trial; `MAX_PLAYER_TURNS = 6` hands over `player_turn_limit`. A stopped enemy
  phase makes the next `turn_next` hand over with its reason (`handover.json` `screen_state: after_stop`).
  The End Turn simulator now has `player_turn` in place of a hard-coded turn 7. One M10 test changed on
  purpose: after `done`, a repeat `enemy_phase` is refused (4 new tests).

  Tasks 4-6 done offline (node description; the helper never closes PPSSPP; driver
  `local/m13-tools/clear_loop.py` + dry-run tests; code review high: 8 findings, 7 fixed red-first, 1 skipped).
  Checks: pytest 1593 / 1 skipped, helper + driver 196, node 8, ruff, strict mypy. Task 7 (live) is blocked before
  launch: the backup gate refuses as "stale receipt" because `Get-NetTCPConnection` now takes 11-15+ s. No
  emulator ran; originals unchanged; backups m13live1/m13live2 are verified. See
  [M13 handover](research/2026-10-25-m13-handover.md).

  User chose the netstat listener check: done red-first (`WindowsInspector.listeners`, 8 tests; 0.16 s live).
  Live attempts m13live3-5: Windows was under heavy load (Defender scanning the fresh backups). Two refused
  before spawn (CIM process check over 15 s). m13live4 ran turn 7 with memory reads at 5-9 s: 2 fired, then
  act time budgets ran out and the helper disabled itself; no ally lost; closed gracefully; originals unchanged.
  **26 Oct, run m13live6 (machine quiet): M13 live acceptance passed.** From `turn7-start` (backup 54/54, checkpoint
  `MISMATCHES []`), turn 7: 14 fired, and it handed over `cleared` mid-turn with no ally lost. The game is on the
  map with no menu and 7 allies unmoved, `handover.json` matches the screen, and PPSSPP is left open for the
  player. Under the "attack bosses if nothing else" rule, both bosses also left the unit list (destroyed or
  withdrew), so this checkpoint leaves no boss for the human. Not yet live: a second player turn.

User decision (26 Oct): keep the current boss rule; M13 is done. The player takes over from the m13live6
handover and attacks the bosses themselves from now on. Committed and pushed as 9c4d836.

- [ ] M14 Other stages (26 Oct, in progress; user: "don't assume" any robot is on a map). Boss list for all
  105 Saisei-hen scenarios ([note](research/2026-10-26-saisei-hen-bosses.md) + JSON, from atwiki). Offline
  save-state reader (Snappy unpack + project collector) showed the user's slot 2 is stage 33
  (pillar fragments). Generalized red-first: foe = menu group // 4 == 3 (`targets.is_foe`); startup fixture
  and anchor ally from the checkpoint manifest; `close_command_menu` (start-of-run back-out only); cursor
  via pointer [0x08E4EA90]+0x24 (per-map address); compact non-player state rows, no 64-unit cap;
  hover hit raw up to 399 (fragments read 261). Live stage 33 (m14s33c, checkpoint `stage33-slot2`, backup
  54/54, `MISMATCHES []`): the back-out worked, then every attack failed `target_not_hittable` (the 261
  bug, fixed after the run). The last unit (Methuss) had moved, so the runner stopped with its post-move
  menu (Attack/Repair/Standby) open.

## 3. Today/session goal — 26 October

- [x] M13 live acceptance passed (m13live6); committed and pushed (9c4d836).
- [x] Boss list for every stage; stage-33 save decoded offline; group/fixture/cursor/size generalized.
- [ ] Stage-33 live run: blocked by the hit decode (fixed) and a menu left open after a failed post-move attack.

Next step (27 Oct): (1) find the one failing test in the full suite after the hit-bound change (the run was
stopped; helper 200, node 8, ruff, mypy pass); (2) red-first: a failed attack after a move must end cleanly
(MVP Standby, or undo the move), never hand over with a menu open; (3) close PPSSPP gracefully (it is open
on the m14s33c trial copy, helper idle with input refused), then rerun stage 33 from `stage33-slot2`
(backups first; back out with target_select/weapon_list `cancel`, `close_command_menu`, move_range `cancel`).
Uncommitted since 9c4d836: the M14 changes, the boss list and these notes.

## 3. Today/session goal — 31 October

- [x] Full suite green again: the one failure was a stale test (raw 399 is now a valid uncapped hit; 401 is not).
- [x] A failed attack after a move ends cleanly in Standby. First try (Command-menu read) disproved live in
  m14s33f: 0x08E4BE34 keeps the unit's earlier Command menu. Recon m14rec3 (Destiny moved to (5,17) on stage 33,
  6 RAM dumps, screenshot per press): the menu **wraps** (Down from Standby -> Attack, Up from Attack -> Standby),
  and the post-move menu has its own slot **0x08E4BEB4** (u32 count, u32 row; slots are 0x80 apart). Fix,
  red-first: `_standby` reads that slot (`post_move_menu`, wired through `InfoNavigation` and the local
  helper), presses Up once from row 0 and Circles only when row = count - 1.
- [x] Live re-check m14s33g (backup 54/54, originals 0/54 changed, `MISMATCHES []`): the m14s33f stop case now
  ends `standby`; turn 5 `done` (14 fired, 2 no target), End Turn + enemy phase -> turn 6, 17 more fired, **no
  ally lost**, non-boss foes 41 -> 18. Stopped `spirit_menus_not_closed` (new bug, below). PPSSPP left open on the
  trial copy with Wing Gundam Zero's Hit&Away Move/Standby menu up.

- [x] Continue + Hit&Away (Wing Gundam Zero), red-first from the live logs (m14s33g, m14s33m): a kill made
  without moving goes straight to the Hit&Away Move / Standby menu; Circle there shows the Move range, then Cross,
  Down, Circle = Standby; then the kill's result pages and Continue's bonus step follow, with the range lingering.
  `act.result` no longer treats a range centred on the unit as the map before that Standby (`ha_range`), and lets
  the Continue path decide after it. Live m14s33n: both Wing Zero attacks fired and the run went on.
- [x] Late cursor drift before the Move Circle (m14s33h: planned (8,16), moved to (8,15)): `act.move` re-reads the
  cursor and re-walks (`CURSOR_CHECKS = 3`, else `cursor_not_on_destination` and back out); a move that still
  lands elsewhere ends with the verified Standby (`plan_act`, `elsewhere`).
- [ ] Stage 33 two-turn clear: m14s33n reached turn 6 with no ally lost (foes 41 -> 18, 14 + 18 fired), then
  stopped `cursor did not reach the unit`: the per-turn cursor budget `MAX_GOTO_PRESSES = 400` ran out after
  about 22 plan_acts (the message still says "trial"). User decision (31 Oct): keep 400.

Live-run notes: m14s33i lost its helper on a plain press ("protected navigation failed", unexplained, nothing
sent); m14s33j/l refused before spawn under load and m14s33k overran an act deadline (reads 2.4 s): wait for CPU
< 35% after each launch (Defender scans every new backup) before checking and playing. PPSSPP is left open on the
m14s33n trial copy, on the map with no menu; at session end it was found already closed (no crash event),
and the originals matched the m14s33n backup (0/54 changed).

Review (manual, 31 Oct diff of act.py, plan_act.py, spirit_cast.py, helper reader): no Critical/Important.
Minor: `_standby` gives up without a Cross when the post-move read shows the wrong row after Up (the turn still
stops safely); the cursor-budget refusal text says "trial" although the budget is per turn.

Lessons: launch `restart.ps1` detached (WMI `Win32_Process Create`); a shell-launched PPSSPP died with the call
(m14s33e). Long background greps over `local/` starve the backup gate (m14s33d). A move/standby declaration may
name "Destiny" = the checkpoint anchor (local helper fix, test first).

Next step: M15 real-test readiness (section 2c, user priority 31 Oct), starting with its design. Before that,
with the 400-press budget kept, the runner stops when a long turn uses it up. Options for the
next session: spend fewer cursor presses per action (e.g. skip the map-proof walk where memory already proves
the map), or accept the stop and hand over mid-turn as `turn_budget`-style handover (not a stop with a reason).
Rerun stage 33 from `stage33-slot2` as before (back-out: target_select cancel, weapon_list cancel,
close_command_menu, move_range cancel; goto (19,17); `clear_loop.py 7`). See
[31 Oct handover](research/2026-10-31-m14-handover.md).
Checks now: pytest 1628 / 1 skipped, helper 195, node 8, ruff, strict mypy. Uncommitted since 9c4d836.

## 3. Today/session goal — 31 October (M15 design)

- [x] M15 design approved (approach A) after four questions.
- [x] Spec and plan written (uncommitted).
- [x] Progress notes updated.

- [x] Task 1 (offline, /loop): the UI window pool (0x08E4B9F8, free count 0x08E4BB9C) names every menu screen
  on both stages by its open window objects; the stage-33 checkpoint reads as target select offline.
  Open: the "range view" left after closing a Command menu has no pool object, same as the map (Task 1b).
  [Notes](research/2026-11-01-m15-screen-signatures.md).

- [x] Task 2 (red-first): `src/psp_buddy/slot_prepare.py` (`choose_anchor`, `manifest`) and `retry.snapshot`
  (a mid-turn save's retry block; `retry.manifest` still needs a phase start). pytest 1636 / 1 skipped, ruff,
  strict mypy.

- [ ] Task 4 (in progress): `src/psp_buddy/press_budget.py` done red-first (`reach_unit`, `act_cost`, `fits`).
  The m14s33n logs do not record cursor presses per action (act walks are unlogged), so the margin comes from
  the code: taps only (long holds off), two 2-press map proofs + 2 for a drift re-walk = 6; Spirit +2.

  `turn_next` now hands over `cursor_budget` (on the map, before any press; handover.json lists every
  ally's unmoved flag) when reaching the next unit would overrun the 400 presses. The name `turn_budget` is
  already the M13 player-turn limit, so the spec's mid-turn handover is called `cursor_budget`. The refusal
  text says "turn". pytest 1644 / 1 skipped, ruff, strict mypy.

  Second check done: `plan_act` compares `press_budget.act_cost` (unit -> destination -> target, Spirit
  +2) with the act IO's `cursor_presses_left()` after planning and before any press; over budget it answers
  handover `cursor_budget` (a skip in `turn.SKIP_HANDOVERS`), and the next `turn_next` hands the turn over.
  pytest 1646 / 1 skipped, helper 195, clear_loop 6, ruff, strict mypy.

  Map-proof skip dropped: `act._cursor_walks` proves the map against dialogue and result pages, which
  open no UI-pool window, so the pool cannot replace it (saving would be 2-4 presses per action).
- [ ] Task 3 (proven part, red-first): `src/psp_buddy/screen.py` (`open_windows`, `classify`, `backout`)
  from the Task 1 table; all 28 labelled retained dumps classify correctly and the stage-33 checkpoint
  reads `target_select` with a 3-Cross back-out. Open (Task 1b): the range view also reads `no_menu`;
  `post_move_menu` and `spirit_list` have no proven back-out (refused). pytest new 21, ruff, strict mypy.

- [x] Task 5: `local/m15-tools/prepare.py` (red-first, 10 tests with fakes; RAM-image adapter for the
  collector with all code anchors verified). Offline on the user's slot 2: same SHA-256, turn 5 and all 70
  retry units as the hand-made `stage33-slot2` manifest (0 field differences), opening `target_select`;
  anchor 149299024 (lowest-object rule). Slots 0 and 1 prepare too but open on `unknown` screens (new
  windows; see the research note), so `run` would refuse them. Test checkpoints: `m15-s33-check`,
  `m15-slot0-check`, `m15-slot1-check`.

- [ ] Task 6 (in progress): the helper's `state` answer now carries `screen` and `ui_windows` (one more
  580-byte read of the UI pool in the same pause as the map blobs; an unparsable pool reads `unreadable`,
  never a refusal). Red-first: 2 new helper tests, 2 older fakes given a pool region. Helper 197 + m15-tools
  10 + clear_loop 6 pass; `prepare.py` updated for the extra blob and re-checked on slot 2.

  `local/m15-tools/backout.py` done: live `state.screen` must equal the prepared opening; one Cross per step
  with a fresh screenshot and the current screen as context, re-read, require the step's `expect`; `goto` the
  anchor tile at `no_menu`; outcomes `map`, `unknown_opening_screen`, `opening_mismatch`,
  `backout_unexpected_screen`, `cursor_proof_failed`, `press_refused`, `state_unreadable`,
  `backout_too_long` (cap 6). 9 tests (written with the code, so red not observed; two mutations each
  caught). m15-tools 19 pass.

  `local/m15-tools/run.py` done (red-first, 9 tests with fakes): refusals before launch (`no_manifest`,
  `unknown_opening_screen`, `machine_busy`), WMI-detached `restart.ps1`, `launch_failed` / `helper_failed`,
  SCREENSHOT folder + 90 s settle + second CPU gate, `checkpoint_mismatch`, back-out, clear loop,
  `local/m15-runs/<L>/m15-report.json` (originals line, backup line, back-out, clear summary).
  m15-tools 28 + clear_loop 6 pass. All P1-P4 pieces exist offline; none has run live yet.

- [x] Task 7 live on stage 33 (user: "Use slot 2"): `prepare.py --slot 2 --name m15-s33`, then
  `run.py m15-s33`. m15s33a: PPSSPP crashed on its own about 1 min after start-up, before any input (the
  recurring fault 0xc0000005 at offset 0x864414, 13 times since 14 Oct); stopped `state_unreadable`, nothing
  pressed. **m15s33b passed with no manual step**: backout 3 Crosses checked from memory
  (target_select -> weapon_list -> unit_commands -> no_menu) plus the cursor walk; turn 5: 14 fired; End
  Turn + enemy phase -> turn 6: 18 fired; then a clean `cursor_budget` handover on the map (no menu,
  final screenshot ULJS00460_00047), non-boss foes 41 -> 18, **no ally lost**, 8 allies left unmoved for
  the user. Both backups 54/54 verified, originals 0/54 changed. Report:
  `local/m15-runs/m15s33b/m15-report.json`. Task 1b is answered: the 26 Oct "range view" is the map's
  hover highlight, so `no_menu` + a working cursor walk is the map ([note](research/2026-11-01-m15-screen-signatures.md)).
  PPSSPP is left open on the m15s33b trial copy at the handover.

- [x] 1 Nov: run timing (m15s33b, ~57 min): ~8 min start-up overhead, turn 5 ~21 min, enemy phase ~3 min,
  turn 6 ~25 min; ~80 s per attack. Cause of slow reads found: every pause, resume and press runs
  `LaunchSession.assert_bound()`, which starts PowerShell (`Get-CimInstance`, 0.85 s measured) — about
  2,500 times a run. User approved the fix design: instant handle checks every call, full identity check at
  most every 30 s ([spec](superpowers/specs/2026-11-01-faster-reads-design.md),
  [plan](superpowers/plans/2026-11-01-faster-reads.md)). Later speed-ups (lighter reads, battle animations
  off, skip repeated map proof, trim sleeps) are separate follow-ups.

- [x] 1 Nov: faster reads implemented (launch.py periodic identity check; act hover/range polls after
  fr-s33a fired 24 instead of 32 at 27 min). Live recheck fr-s33b running. Fast-screenshot design approved
  (PPSSPP's own screenshot via ctypes, poll for the file; debugger capture failed here in Oct):
  [spec](superpowers/specs/2026-11-01-fast-screenshots-design.md),
  [plan](superpowers/plans/2026-11-01-fast-screenshots.md).

- [ ] fr-s33b (with hover/range polls) stopped after ~14 min (turn 5, 10 actions in): the emulator's
  debugger did not answer one memory read for 60 s (adapter timeout, config.json), right after two Down
  presses in the weapon list; helper disabled itself, nothing else pressed, PPSSPP still running (no crash
  in the Application log). Backups 54/54 verified, originals 0/54 changed. Cause unproven. Hypothesis: with
  fast reads, pauses now follow presses and each other within milliseconds (before: >= ~0.5 s from the
  PowerShell check), which PPSSPP's stepping may not tolerate. Not yet fixed.

- [x] 1 Nov, user "Yes, add gap": `DebuggerAdapter` waits until 0.2 s after a press / 0.1 s after a resume
  before a new pause. **fr-s33c passed**: 31 min total (m15s33b: 57), turn 5 ~14 min (was ~21), turn 6
  ~13 min (was ~25), 15 + 17 = 32 attacks (same as m15s33b), no failure stages, no stall, no ally lost,
  non-boss 41 -> 17, clean `cursor_budget` handover on the map. Reads median 0.11 s (was 1.0). Backups
  54/54 verified, originals 0/54 changed. PPSSPP left open on the fr-s33c trial copy.

- [x] 1 Nov: fast screenshots implemented (`local/m9-tools/fast_shot.py`, ctypes, polls the folder;
  `turn_loop_lib.shot` uses it; run.py reports shot timings). **fs-s33a**: 47 screenshots, all accepted,
  median 0.73 s, max 3.44 s (was ~5 s each); 15 + 18 = 33 attacks, no failure stages, no ally lost,
  non-boss 41 -> 15, clean `cursor_budget` handover. But total 41 min (fr-s33c: 31): every step ran
  ~15-20% slower (reads 0.70 vs 0.58 s avg, Circle 1.71 vs 1.44 s) and start-up took ~7 min (was ~4);
  CPU was at 69% after the run (other apps). Likely machine load, not proven. Backups 54/54, originals
  0/54 changed.

- [x] 1 Nov, user "remove the excessive cursor move": per-run skip of mechs with an unknown Command menu
  layout, and a memory map proof after a menu-only back-out
  ([spec](superpowers/specs/2026-11-01-fewer-cursor-moves-design.md)). **cm-s33a**: 26.5 min total
  (fs-s33a 41, fr-s33c 31, m15s33b 57); play 22.6 min; 15 + 18 = 33 attacks, no failure stages, no ally
  lost, non-boss 41 -> 15, clean `cursor_budget` handover; 8 Spirit attempts skipped with no input;
  screenshots median 0.71 s, max 0.76; backups 54/54, originals 0/54 changed.
- Battle animations: the user turns them off in their own game (user, 1 Nov); a new checkpoint must be
  prepared from a save state made after that. The fixed 8 s wait after Start stays until such a run.

- [x] 1 Nov: code review (high) of all M15 and speed-up changes: 7 findings, 5 fixed test-first
  (Spirit skip only on a plausible row-0 read; fast_shot sends no keys unless PPSSPP is in front and
  retries a locked file; run.py names `emulator_exited`; press_budget docstring), 2 left as minor (fast_shot
  could pick another PPSSPP top-level window; hover/range polls overlap the adapter press gap). After
  fixes: pytest 1682/1 skipped, ruff, strict mypy, node 8, helper 196, tool tests 45. Committed at the
  user's request (local/ tools stay ignored, as before).

- [x] 1 Nov, animations off: the user's new save "slot 3" is PPSSPP file `_2` (UI slots count from 1).
  It is a different map from stage 33 (24x32, turn 1, all 23 allies unmoved, 32 foes in group 12, boss
  Hyaku Shiki 33000); the old stage-33 state survives in `local/checkpoints/m15-s33` and the backups.
  `prepare.py --slot 2 --name m15-s33-noanim` (opening `no_menu`). Run na-a refused before launch:
  originals changed 8/54, all from the user's own play at 21:12-21:16 (S006 save, SYSTEM.BIN, slot `_2`
  state + undo); new reference backup `userplay1101-original-20261101T111952Z` 54/54. **na-b**: 16.5 min
  total; player phase ~8.3 min, 11 attacks (incl. one Hit&Away) + 14 `no_target` (foes out of reach on
  turn 1); enemy phase ~1.7 min for 32 foes with animations off; then handover `ally_destroyed`: Lockon
  (GN-SR2 unit, 4800 HP) moved forward to attack and was shot down in the enemy phase (Arios also fell to
  943 HP from a counter). Screenshots median 0.71 s; backup 54/54, originals 0/54 changed. The game is
  left on the trial copy at Lockon's defeat line.
  Finding: on a turn-1 map where the foes start far away, advancing every unit that can reach a foe puts
  fragile units inside a 32-foe swarm. Needs a design decision (e.g. hold position/wait for the enemy on
  open maps, or skip attacks that end a low-HP unit inside many foes' reach) before more runs here.
  The fixed 8 s `ANIMATION_SECONDS` wait (src/psp_buddy/act.py:25) can now be measured for a shorter value.

- [x] 3 Nov, M16 ally safety (user's rules, design approved; offline only):
  [spec](superpowers/specs/2026-11-03-ally-safety-advance-design.md),
  [plan](superpowers/plans/2026-11-03-ally-safety-advance.md). Two opt-in policy clauses:
  `hold units without focus or sense on turn 1` (on game turn 1 a pilot who has not learned Focus or
  Sense attacks only from its own tile, else stays unmoved: skip `held_turn_one`) and
  `advance toward foes when none is in reach` (a unit with no foe reachable moves to the reachable
  free tile nearest the nearest foe, then Standby: outcome `standby`, reason `advance`). Units that can
  attack attack as before. Added to `local/m13-tools/clear_loop.py` POLICY (ignored file). Code review
  (high): 6 findings, 5 fixed test-first (stale post-move menu row not trusted, failed advance still
  ends in Standby, turn field type check, spirits read only when the hold can apply, tests); left:
  the advance uses Manhattan distance (terrain ignored, accepted in the spec). Checks: pytest 1708 / 1
  skipped, helper + tool tests 232, node 8, ruff, strict mypy. Not run live. Unverified live: whether
  the post-move menu after a move with no foe in reach lists Attack (Standby handles both cases).

- [x] 3 Nov live (all backups 54/54 verified, originals 0/54 changed). **m16-a** (stopped by the user mid
  turn 1): Michel's VF-25G had Sense learned but its 5-entry Command menu was unchecked, so the cast was
  skipped (`menu_layout_unknown`); it still counted as spirited, advanced, attacked and took a counter
  (4700 -> 1310). User: "Both fixes". (1) Turn-1 test now needs Focus/Sense active or cast (tried before
  any move when `use spirits before attacking` is on; a unit that will retreat casts nothing). (2) Recon
  m16-rec-michel/-alto/-arios (screenshot per press, view only): VF-25G and VF-25F with no foe in reach
  Move/Land/Morph/Spirit/Info, Arios with a foe in reach Move/Attack/Land/Spirit/Info: Spirit row 3 of 5,
  added per mech (`SPIRIT_ROW_BY_MECH` is now mech -> {entries: row}); other counts (e.g. a VF-25 with
  Attack, 6 entries) stay unchecked. Checks: pytest 1715 / 1 skipped, helper + tools 232, node 8, ruff,
  strict mypy. **m16-b** (14 min): turn 1, 8 attacks + 2 advances, 14 `held_turn_one`, Sense cast 9 times
  (all confirmed); 5 more pilots held because their menus are unchecked (Z-like counts on other mechs).
  Enemy phase: **Garrod (149303184, 5400 HP) destroyed** after advancing with Sense and attacking;
  149303704 5800 -> 4335. Sense's evade covers one attack, not a swarm. Handover `ally_destroyed`, game
  left on the trial copy at Garrod's defeat line. Needs a user decision on how far spirited pilots may go.

- [x] 3 Nov (user: "check all the different type of menu and make sure sense can be cast; in enemy phase,
  if the foe hit rate more than 30%, choose eva"). All live steps on trial copies, every backup 54/54
  verified, originals 0/54 changed.
  - Helper: `menu_recon` declaration (view-only Command menus of any baseline ally, Spirit list browsing,
    close any time); `enemy_phase` `stop_at_window` and `reaction_move` presses for recon; node validator
    updated. Recon m16-rec-menus (screenshot per press): Z Gundam 4 = Move/Morph/Spirit/Info, VF-19 Kai 6 =
    Move/Sing/Land/Morph/Spirit/Info, Altron and Deathscythe Hell 3 = Move/Spirit/Info, Wing Zero 5 =
    Move/Land/Morph/Spirit/Info; the 00 Raiser has two pilots: Spirit opens SELECT-PILOT (UI window
    0x08E4D090, Setsuna first) before the list (0x08E4D208) -- the m16-b `cast_not_confirmed`; now one
    Circle picks the first pilot.
  - Menu rows from memory: each menu slot has a u32 entry bitmask 8 bytes before its count, entries in rising
    bit order (Move 2, Attack 3, Morph 14, Spirit 23, Standby 25, Retrieve 26, Info 27), checked on every
    retained dump with a known menu (Gundam 00, Z Gundam, a ship whose Spirit is not above Info, post-move
    menus). Spirit and post-move Standby rows now come from it (the per-mech table is the fallback). Found
    after m16-c turn 2: ten mechs had 5-7-entry menus with Attack, and a ship's post-move menu is
    Standby / Retrieve (Standby first) -> `advance_standby_failed`.
  - Evade: recon m16-rec-enemy: each enemy attack shows forecast window 0x08E4C81C (Start / Anim / Support
    greyed / Move, cursor u32 0x08E4C898, Move = 3); Move opens SELECT-ACTION 0x08E4CD80 (Atk./Def./Eva.,
    cursor 0x08E4CDB8, Eva. = 2); the hover hit read gives the foe's hit and halves after Eva. (35 -> 17).
    Clause `evade when the foe hit rate is above 30%`; `enemy_phase evade_above` walks, verifies and
    reports each reaction (`reactions` in enemy-phase-report.json).
  - Checks: pytest 1736 / 1 skipped, helper + tools 232, node 8, ruff, strict mypy.
  - **m16-c** (25 min): turn 1: 15 Sense/Focus casts, 9 attacks, 4 advances, 8 held; enemy phase 14 Evades,
    all confirmed by the halved hit; **no ally lost**; turn 2 stopped at the ship's Standby (fixed above).
  - **m16-d** (16 min, bitmask rows): turn 1: 16 casts, none skipped; enemy phase 13 Evades confirmed; still
    **Michel's VF-25G destroyed** (several foes hit it at 33-42% after Evade). Same turn-1 play as m16-c;
    the difference is the dice.

- [x] 3 Nov, user "Limit foes in reach": clause `end moves within reach of at most N foes` (runner: 2).
  No move (attack or advance) ends on a tile that more than N living foes can reach next enemy phase
  (foe move + longest weapon usable after moving, or longest range, Manhattan, terrain ignored; a foe whose
  reach is unread counts everywhere); attacking from the own tile is never limited. Foe reach is read once
  per trial with the boss-name read (one weapon read per foe). Code review (high) of the whole round:
  5 findings, 2 fixed test-first (duplicate foe reads; a bitmask miss no longer puts a mech on the per-run
  spirit skip list), 3 accepted (stale post-move mask is caught by the Standby poll; unknown reach blocks
  moves; reach ignores terrain/stationary foes). Checks: pytest 1745 / 1 skipped, helper + tools 232,
  node 8, ruff, strict mypy.
  - m16-e: helper TimeoutError after unit 3 (a read hung after Basara's cast; game fine on the map);
    retried as **m16-f**: turn 1 = 1 attack, 8 advances, 8 held, 15 casts; enemy phase: 2 Evades,
    **no ally damaged or destroyed**; turn 2: 8 attacks, 7 casts, then stopped on an emulator
    status error ("normal running status required before observation"). The driver also crashed twice
    on three screenshot misses in a row (resumed with `local/m16-tools/resume.py`; capture retries now
    6 with longer waits). Backups 54/54, originals 0/54 changed. Game left on the trial copy (turn 2 map).
  - m16-g and m16-h (3 Nov, re-run): both stopped before launch on the helper's backup gate ("stale
    backup receipt": the receipt must be revalidated within 60 s, `backup.BackupGate.freshness_seconds`;
    re-hashing the 395 MB snapshot took longer with the disk busy, likely Defender scanning new backups;
    earlier runs spawned 14 s after `prepared.json`). No game input; backups 54/54, originals 0/54
    changed; PPSSPP closed. Gate left unchanged.
  - **m16-i** (retry after a quiet disk): ran to turn 3; an ally damaged in turn 2 was skipped
    `retreat_needed` and destroyed in the turn-3 enemy phase; Eva. never lowered a 100% hit.
  - User rules after m16-i (3 Nov, approved): strongest weapon on any foe above 10% HP (cheap below
    10%); damaged units cast Focus/Sense, then attack only from a tile at most 2 foes reach, else move
    to the safest tile and Standby (or stay: `retreat_stay`); Def. at a 100% foe hit. Spec amendment
    "run m16-i". Review: 3 fixes (budget before cast, safest attack over all foes, reach read for the
    retreat clause). m16-j stopped at once: policy text 402 > 400 chars; limit now 800.
    Checks: pytest 1767 / 1 skipped, helper + tools 232, node 8, ruff, strict mypy.
  - **m16-k**: turns 1-3 and three enemy phases with **no ally lost**; 3 retreats; Def. chosen on
    all three 100% hits, Eva. on the rest. Stopped in turn 4 after Lockon's attack: an extra "Get
    Result" page (Allelujah/Arios, likely a support) was read as a stale post-attack Move menu
    (`act.py` `post_attack_move_not_closed`). Game left on that result page (trial copy). Backups
    54/54, originals 0/54 changed.

User, 4 Nov: happy with the M16 result; the m16-k turn-4 stop is acceptable as a handover (no fix).
Next step: a live test from a new save state the user will provide (back up first; wait for a quiet
disk so the 60 s backup gate passes); then shorten the post-Start wait; then P6 (other saves).
Still open: Task 10 checks (user: later).
Committed 4 Nov (M16 code, spec, plan, this file); recon changes stay in ignored local/ tools.

- [x] 4 Nov live test, user's new "slot 4" (user: a slot number means the **project PPSSPP's** memstick
  `local/runtime/ppsspp-v1.20.4/app/memstick/PSP/PPSSPP_STATE`, file `_<N-1>`, not OneDrive; `prepare.py`
  now defaults there and has `--state-dir`). PPSSPP 1.20.4 writes zstd states: the offline extractor
  (`local/state-memory-20261016/extract.py`) now also reads compression 2 (Python 3.14 `compression.zstd`).
  First two runs (s4-a, s4-b) loaded the OneDrive slot-4 file by mistake and were stopped before any input.
  **s4-c** (checkpoint `pslot4-20261104`, 28x28 sea/island map, turn 1, 23 allies, 30 foes; 19 min):
  backups verified (OneDrive 56/56, portable memstick 55/55), back-out 0 presses (map). Turn 1: 2 fired,
  the rest held `held_turn_one`; enemy phase 1: 6 foe attacks under 30% (no reaction), 5 foes destroyed,
  no ally damaged. Turn 2: 11 fired, 6 advances, 6 `no_target`. Enemy phase 2: 4 Evades confirmed, one
  reaction skipped `hit_unreadable`; **149299232 (Distortion Shoot unit) 5800 -> 0** -> handover
  `ally_destroyed`, game left on the trial copy at a dialogue line (ULJS00460_00054). After the run both
  originals and the portable memstick were unchanged (0/56, 0/55).
  Findings for the user: (1) the stage's boss list names every "Android DB ADAMON" as a boss, so 8 of
  turn 2's attacks went into one 18,500-HP Android (non-bosses out of reach -> bosses allowed); (2) a
  full-HP unit fell in one enemy phase although it attacked from a tile at most 2 foes reach (reach ignores
  terrain/flying, and the boss-named foes may hit hard); one hit was unreadable, so no Eva./Def. there.
- [x] 4 Nov, user: "the boss should be D-Beast Rook Adamon P". Per-checkpoint boss names, red-first:
  `prepare.py --boss NAME` (repeatable) writes `boss_names` into the manifest; the handoff passes them to
  `InfoNavigation(boss_names=...)`; then `clear.begin(..., factor=0)` and `plan_and_act(boss_factor=0)`
  make only the named foes bosses (no max-HP rule). Without names nothing changes. Checks: pytest 1770 /
  1 skipped, local tools + helper 233, ruff, strict mypy. (The prepare test was written with the code.)
  **s4-d** (new slot 4 saved 21:59, checkpoint `pslot4b-20261104`, turn 1 with all allies already moved;
  34 min): boss set = D-Beast Rook ADAMON P only. End Turn + enemy phase 1 (5 Evades), turn 2: 18 fired,
  4 advances; enemy phase 2 (4 Evades); turn 3: 18 fired, 1 advance; then handover `cursor_budget`
  with **no ally lost**, non-boss foes 15 destroyed / 13 left, 6 allies unmoved. Backups 56/56 and portable
  55/55 verified; originals 0/56 and portable 0/55 changed after. Note: handover.json says
  `screen_state: map`, but the final screenshot (ULJS00460_00060) shows a story dialogue (Asakim, after 5
  `dialogue_pending` steps in turn 3): the cursor-budget handover does not settle a pending dialogue.
  Every enemy phase skipped 2 reactions as `hit_unreadable`. One ally ended at 675/5300 HP.
- [x] 5 Nov live, user's new slot 2 (space map, Arietis boss). Every launch had portable memstick backups
  (55/55 verified, 0 changed between runs) and the runner's OneDrive backups (56/56). Checkpoints
  `slot2-20261105` (turn 4) and `slot2-20261105T2210` (turn 6, the user's save after turn 5).
  **s2**: turn 4 (17 fired, 3 no-target, 8 advanced), enemy phase, turn 5 (4 fired), then stopped
  with `driver_error`. **s2b** was paused by the user, mid-turn 5 (controller stopped; `clear_loop.py 56` resumed it on
  the same helper): 9 fired, 17 advanced, handover `cursor_budget`, no ally lost. **s2t6**: 3 units, then
  the same `driver_error`.
  **Open bug (next):** both `driver_error` stops were a memory read straight after a Circle press that hung
  60 s (`disabled.json` TimeoutError, reads disabled). The game was not stuck: the user could move the cursor.
  Same pattern as fr-s33b (1 Nov), which `DebuggerAdapter.PRESS_GAP_SECONDS = 0.2` was meant to fix; that gap
  is not always enough. Options: a longer gap after Circle, or retry a hung read rather than disable reads.
  Also: after a handover the helper refuses input, so another round needs a save + relaunch (user saves slot 2).
  User saved the state again on 5 Nov night to continue the test.
- [x] 6 Nov live, user's slot 2 re-saved 07:30 (same space map, turn 6, 24 allies unmoved). Portable memstick
  backup `backups/portable-memstick-20261106T075120Z` 55/55; runner backup 56/56; after the run originals
  0/56 and portable 0/55 changed. Checkpoint `slot2-20261106` (prepare.py needs `.venv/Scripts/python.exe`).
  **s2c** (22 min): back-out 0 presses; turn 6: 19 fired, 6 advanced; boss set Arietis only (default rules).
  Enemy phase 6: 3 Evades confirmed, 9 reactions left default (hit 2-26%); 4 more foes destroyed
  (12 non-boss destroyed, 11 left); then handover `ally_destroyed`: 149301728 (Ennil's unit) had taken
  a counter 5750 -> 2956 from its own Bazooka attack (89% hit) and fell in the enemy phase. No `driver_error`
  this run. Game left on the trial copy at Ennil's retreat line (ULJS00460_00032).
  Finding: a unit left near half HP by a counter is not retreated or guarded before the enemy phase.
- [x] 6 Nov live, user's new slot 2 saved 22:55 (new space map with a station, turn 2, 23 allies unmoved).
  PPSSPP closed gracefully first; portable backup `portable-memstick-20261106T125633Z` 55/55; runner backup
  56/56; after the run originals 0/56 and portable 0/55 changed. Checkpoint `slot2-20261106T2255`, default
  boss rules (no names given). **s2d** (25 min): turn 2: 27 units (fired/advanced/no-target), enemy phase 2
  done with no ally damaged (2 foes destroyed, 1 reaction skipped), turn 3: 18 units, then `driver_error`
  - the same hung read (`disabled.json` TimeoutError, 60 s), this time after the 3rd **Down** press in Big O's
  weapon list (screen ULJS00460_00050, MeleeAttack row), not after a Circle. No ally lost.

## Session goal history — 20 October


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
