# Spirit menu view-only recon — 23 Oct 2026 (M11 Task 2)

Run `local/move-attack-trial-20261017/m9livesp1-run-20261023T124311Z`, backup
`backups/m9livesp1-original-20261023T124311Z` (46/46 SHA-256 verified). Declaration `{"unit":"Gundam 00","actions":
["spirit_recon"]}` (kept as `action-declaration.spirit-recon.json`; `action-declaration.json` is back to `act`).
Handoff unit objects gained `Gundam 00: 149303600` (backup `navigation_handoff.py.bak-20261023`).

## Steps (all agent-driven, nothing cast)

Screenshot frames ULJS00460_00000-00009 (runtime memstick SCREENSHOT folder).
1. Map, turn 7, cursor already on Gundam 00 (17,4); state: Setsuna (pilot_id 242) SP 55, HP 5000, EN 121.
2. `open_unit_menu` -> Command menu Move / Attack / Spirit / Info (Move highlighted).
3. `menu_direction` down x2 -> Spirit highlighted; RAM dump 1.
4. `open_spirit` (Circle) -> **the spirit list opens directly** (single pilot: no pilot screen). RAM dump 2 (Focus row).
5. `spirit_menu_move` down -> Sense row; RAM dump 3.
6. `cancel` (Cross) -> back to the Command menu with Spirit still highlighted.
After: unit list identical to the start (SP 55). PPSSPP closed gracefully; originals unchanged (0/46 against this and the
previous backup).

## Spirit screen facts

- Layout: pilot portrait, LV, WL (will) 150, SP 55/95; own list (rows with cost): **Focus 15** (row 0, highlighted on
  entry), **Sense 20** (row 1), **Yell 35** (row 2, shown green); right panel "Others Command": Attun, Cheer (other
  pilots' spirits; Cheer in red). Bottom: effect text, target/duration, a strip of spirit kanji; hints START: List,
  Square: Mrk (mark).
- Effects shown by the game: Focus = "Hit&Eva+30%", Self · 1 Turn. Sense = "Casts FLASH & AIM", Self · 1 Turn
  (one sure dodge + one sure hit). Matches the spec's assumption.
- Cursor starts on row 0 each time the list is opened (one observation).
- The Cross from the list returns to the Command menu (not the map).

## Memory (offline decode of dump 2, 23 Oct)

- Pilot runtime = actor +8 -> +4 (same chain as pilot skills). Runtime +0x24 u16 max SP (95), +0x44 u16 SP (55; the
  collector's pilot record +0x3C), +0x46 will (150), +0x4E level (36).
- **Spirit list: runtime +0x5C, six (id, learn level, SP cost) byte triples**, rising learn level; empty = (0,255,255).
  Setsuna: (6,1,15) (9,7,20) (18,31,35) (1,47,35) (2,58,50) (11,64,55). The screen lists exactly the learned triples
  (level >= learn level) in stored order with the stored costs, so **row = index among learned**; id 6 = Focus,
  id 9 = Sense (18 = Yell, unproven name). All 26 units decode plausibly; Focus/Sense are common (Destiny, Z, Arios,
  Strike Freedom, Infinity Justice, Brasta, Shenlong, VF-25F ...). Costs differ per pilot (Focus 10 for one pilot).
  Implemented as `src/psp_buddy/spirits.py` (`decode_pilot`, `read_pilot_spirits`, `choose_spirit`), tests in
  `tests/unit/test_spirits.py`; decoding the live dump gives Sense at row 1.
- Spirit-list cursor row candidates (0 on Focus, 1 on Sense): `0x091FF510` and `0x08DE6BF4`; unconfirmed.
- Spirit names are not in RAM as ASCII/UTF-16 (game text encoding); not needed, ids suffice.
- Mech names decoded (weapons reader): foes Taurus x2 (6600), Euclid (9600), **Vayeate (24000)**, **Mercurius
  (26000)**; **WingGundamZero** (16000) is menu group 4 (third force), never a target.

## Live cast — 24 Oct (run m9livesp3-run-20261023T201408Z)

Backup `backups/m9livesp3-original-20261023T201408Z` (46/46 verified). Declaration `{"unit":"Gundam 00","actions":
["spirit_cast_recon"],"spirit_name":"Sense"}` (kept as `action-declaration.spirit-cast.json`; `action-declaration.json`
is back to `act`). Bridge: `cast_spirit` (one Circle on the declared spirit) and `confirm_spirit` (Yes, unused).
Frames ULJS00460_00000-00014; dumps ram-01 (spirit list, Sense row, before) and ram-02 (map, after).
- **One Circle on the Sense row casts it. No Yes/No dialog.** About 1 s later the screen is the **map with no menu**
  (the game closes the Command menu; frame 7 and frame 8 a few seconds later both show the map). The unit stays
  unmoved (counter 1), cursor still on its tile; select it again to Move/Attack.
- **SP 55 -> 35, exactly the cost**; no other unit field changed (`read_state` diff).
- **Active-effect mask: pilot runtime +0x14 (u16) 0 -> 0x44**, the only other change in the pilot runtime, object and
  unit runtime. The effect strip on the spirit screen (熱魂閃不鉄集必加覚手狙直突幸努乱) then lights 閃 (Flash, bit 2)
  and 必 (Aim, bit 6): the mask follows the strip order. Focus (集) should be bit 5 (0x20), not yet observed.
- Re-opened spirit list: **Sense greyed (green) at the same row**, rows do not shift; Focus still highlighted on
  entry (row 0); "Others Command" lost Attun. Cross returns to the Command menu.
- Lesson: launch the trial from a background task that stays alive (`run_in_background`). Run m9livesp2 died
  silently right after `navigation-ready` because the launching shell ended and took PPSSPP and the helper with it
  (originals unchanged; its backup m9livesp2-original-20261023T200840Z kept).
- After: PPSSPP closed gracefully, originals 0/46 changed against both backups.

Implemented: `spirits.decode_pilot` reports `effects` and `active` (Sense when both Flash and Aim bits are set, Focus
on bit 5); `choose_spirit` skips active spirits. Decoding the two dumps: before -> Sense row 1; after -> Sense active,
Focus row 0.

## Open

Multi-pilot units (a pilot screen may appear); the Focus bit; whether a cast from a different list row scrolls.

## Cast step live — 24 Oct (M11 Task 5/6, runs m11live1-4, m11menu1)

Every run: backup `backups/<run>-original-*` 46/46 SHA-256 verified, PPSSPP closed gracefully, originals 0/46
changed. Code: `src/psp_buddy/spirit_cast.py` (`cast_before_attack`), `plan_act` casts once before the first
`run_act` when the policy has `use sense then focus before attacking`; results and `turn-report.json` carry `spirit`.

- **Casts verified from memory**: Focus on Gundam Deathscythe (SP 59 -> 44, mask 0 -> **0x20**, the predicted
  Focus bit, now observed); Sense on Arios (row 3), Strike Freedom (row 0), Destiny (row 2), Gundam 00 (row 1)
  (SP drop = cost, mask 0x44). Rows deeper than 0/1 work, so the list scrolls/steps as expected.
- **Sense makes the hover hit read 400** (m11live1): decoded as a sure hit (100). The planned hit no longer gates
  the forecast after a cast.
- **Spirit-list cursor candidates (0x091FF510, 0x08DE6BF4) are not reliable**: on a fresh launch they did not read 0
  on an opened list (3 of 4); kept as diagnostics (`list_bytes`) only.
- **Command menus differ per unit (user, 24 Oct; screenshots m11menu1)**: Z Gundam = Move / Attack / **Morph** /
  Spirit / Info. Down x2 chose Morph in m11live3: Z Gundam transformed, took heavy damage and missed the act deadline
  after Start (`fire:act_deadline`). Recon dumps at every row found **0x08E4BE34 u32 entry count, 0x08E4BE38 u32
  cursor row** (Z: 5, rows 0..4; Gundam 00: 4, Spirit = 2; map: stale 4/0). The cast now requires row 0 after the
  Circle and a screen-checked layout (4 entries -> Spirit row 2; Z Gundam 5 -> row 3), else Cross before choosing
  any entry; after Down x row the row must match before the Circle.
- **Menus left open** (m11live2): Dancouga Nova (several pilots; Spirit likely opens a pilot screen) was left on
  the Command menu after two Crosses, locking the map cursor for the rest of the turn. Every Spirit path now proves
  the map from memory (the cursor walks one tile and back) with up to two more Crosses, else the turn stops
  (`spirit_menus_not_closed`).
- Unexplained: Shenlong Gundam's Sense (row 1, SP 51) and Dancouga Nova's Focus spent nothing
  (`cast_not_confirmed`); both closed safely. Needs a screenshot-before-each-press recon (user advice, 24 Oct).
- Boss weapons (user, 24 Oct): Mercurius, Vayeate and Wing Zero take no damage from weak weapons, so the turn
  policy now says `strongest boss weapons above 0%` (strongest weapon at any boss HP).
- **Run m11live4 (with the menu gate)**: Focus (Deathscythe) and Sense (Arios, Strike Freedom, Destiny) cast and
  verified, menu [2, 4] each time; **Shenlong's Command menu has 3 entries** -> skipped before choosing any entry,
  map proven. Non-bosses targeted first (Euclid 149302976, Taurus 149301208). Stopped at Destiny: Sense, then
  HiEnergyBeamGun destroyed Euclid (EN 230 -> 195) but Destiny stayed unmoved (counter 1) and a 53-tile move range
  was shown; the 6 dismiss Circles then opened Wing Gundam Zero's unit info (screenshot ULJS00460_00007).
  `result:result_not_dismissed` stopped the turn. Game rule for an action after a kill: open (ask the user).

## Continue (bonus action after a kill) — 24 Oct (runs m11live5-7)

User: Destiny's pilot has a skill giving a bonus move-and-attack step after a kill. Screens (step by step,
`local/m11-shots/`): Get Result (EXP) -> item bonus page (VernierUnit) -> plain map, Destiny still unmoved
(counter 1). A stale 53-tile Move range stays in memory the whole time, so it cannot tell pages from the map;
the map cursor can (it cannot move while a page is up). In run m11live4 the third Circle landed on the map with
the cursor on Wing Gundam Zero and opened its unit info.
- **Skill id 22 = "Continue"** (Shinn's level-up page lists SEED, PrevailL5, BattleSpr, Continue, Re-Attack =
  ids 36, 12, 9, 22, 2). Also on Gundam 00, VF-25F and Brasta. (A first guess of id 2 was Re-Attack.)
- `act.result`: for a Continue pilot whose target is destroyed and who stays unmoved, Circle one page at a time
  and stop as soon as the cursor walks (`bonus_action`); the next `turn_next`/`plan_act` plays the bonus step.
- Second Destiny kill (m11live7b): Get Result with **Lv up** -> item page (P.TargetLens) -> **level-up page** ->
  a **story dialogue** (Quatre/Trowa) and Destiny counted as acted (no bonus that time). Player-phase story
  dialogue after a kill is not yet handled (the act trial has no press for it); trial closed there.
- m11live7b also fired Dancouga Nova, Baldios, Gundam 00 (Sense), Force Impulse, Ptolemaios; Destiny's bonus-step
  Command menu had an unknown layout (Spirit skipped safely).

## Story dialogues and turn 8 — 24 Oct (runs m11live8-18)

User rule (24 Oct): skip story dialogues with Circle. Seen live: Quatre/Trowa after Destiny's kill (m11live7b),
Trowa **before** the battle after Start when Baldios attacks his unit (m11live9: nothing spent until advanced),
Heero's withdrawal after Destiny's first kill (m11live15). Handling: `act.fire` Circles after 4 empty spend checks;
`act.result` always ends on a proven map (Circle through any dialogue); a dialogue longer than the act budget is
left `dialogue_pending` and the next `plan_act` (or `end_turn open`) settles it first with a fresh budget.
Helper: a collector `agreement failure` while a foe withdraws is now a refused (retried) read, not a disable;
`MAX_STATE_READS` 200 -> 600 (memory-only); the loop retries refused `turn_next` and a missed screenshot.
Launch flakiness: capture timeouts / helper dying after `navigation-ready` (runs 5, 8, 13) and a slow process
inventory (runs 11-12); relaunching worked each time.

**Run m11live18 (backup 46/46 verified): turn 7 `done`** — 14 attacks fired (Destiny twice: Continue bonus),
7 units had no target, Sense/Focus cast on every unit with a confirmed menu, only non-boss foes attacked. Strict M10:
End Turn (system menu checked on screen) -> enemy phase, 4 Circles -> **turn 8, no ally lost**. Gundam 00 survived
at 364/5000 (it died in this phase before M11); Shenlong untouched (2348/5300). PPSSPP closed, originals unchanged.

## Turn-7-done checkpoint for replaying the enemy phase — 24 Oct (user request)

User: save a copy before the enemy turn, then test the enemy phase / counterattacks from it again and again.
- Made in run m11live22 (turn 7 `done` in one go with the post-review code) via PPSSPP **File > Savestate slot >
  Slot 3, File > Save state** (the trial maps no save-state keys; window captures checked each menu). It wrote the
  trial memstick's spare slot file `ULJS00460_1.01_2.ppst`; normal launches keep loading `_1.ppst` (unchanged).
  Copied to `local/checkpoints/turn7-done/` with `manifest.json` (SHA-256, expected Gundam 00 values HP 5000 /
  EN 121 / SP 35). Originals untouched.
- Loading: `Launcher.prepare(checkpoint=(path, sha256))` copies the hash-checked file into the trial's own folder
  (never into the memstick, which seeds the next launch) and starts PPSSPP with `--state` on it; refused when the
  file is inside a save root or its hash changed. Helper: `--checkpoint <folder>`; `restart.ps1 -Checkpoint`;
  `full_run.sh` / `start_only.sh` take it as a second argument. The startup checks now identify Destiny by object,
  mech and pilot (not EN) and take the expected Gundam 00 values from the manifest.
- Replay (run m11cp4, about 8 minutes instead of 30+): loaded at turn 7 with only the 7 "no target" units unmoved;
  the loop skipped them, End Turn (screen checked), strict enemy phase -> **turn 8, no ally lost; Gundam 00
  5000 -> 364, same as the full run** (deterministic).

Use:
```
bash local/m9-tools/start_only.sh <label> local/checkpoints/turn7-done
python -u local/m9-tools/turn_loop.py 40 2
python -u local/m10-tools/end_turn_steps.py open <next_seq>      # check the MENU_SHOT screenshot
python -u local/m10-tools/end_turn_steps.py confirm <seq> <file> <sha256>
```

## M12 Task 1 — Alert and Invincible ids, offline (25 Oct)

- PPSSPP 1.20.4 debugger WebSocket: the subscribers are Breakpoint, CPUCore, ClientConfig, Disasm, GPUBuffer,
  GPURecord, GPUStats, Game (`game.reset`, `game.status`, `version`), HLE, Input, Memory, MemoryInfo, Replay
  (input replay only), Stepping. **No save/load-state event**, so M12 saves through the window menu.
- All 26 pilots decoded from `m9livesp1-run-20261023T124311Z/ram-02.bin` (actor bindings from capture-001-1.json).
  Seen ids: 1-7, 9-16, 18-28, 30-32, 34, 35.
- Hypothesis (not screen-proven): spirit ids follow the effect strip 熱魂閃不鉄集必: 1 Valor (熱血; learned late,
  cost 30-40), 2 Soul (魂; late, 50-55), **3 Alert (閃き; cost 10-15, early)**, 4 Persist (不屈; 10-15),
  **5 Invincible (鉄壁; 15-25)**, 6 Focus (proven), 7 Strike (必中; 15-25, often level 1). 9 Sense is proven and
  breaks the strip order (Sense has no strip effect of its own). Expected mask bits: Alert 0x04 (閃, the Flash bit
  Sense also sets), Invincible 0x10 (鉄).
- Allies with id 3 learned: 149303184 (mech 231, HP 11000, (18,16), SP 19, Alert 15; id 5 at level 28, it is 19)
  and 149304848 (mech 140, (18,7), Alert 10, also Focus). **No ally has id 5 learned on this map**; only Wing Gundam
  Zero (149299544, third force) does: (5,1,15) (3,14,10) (7,27,20) (31,29,45).
- Live proof needed (Task 2): Wing Gundam Zero's pilot status screen should list ids 5, 3, 7 by name, proving both
  names in one view-only visit; one Alert cast on 149303184 (SP 19 -> 4, mask +0x04 expected). The Invincible bit
  cannot be cast-checked here; its cast check falls back to the SP drop (it cannot trigger for allies on this map).

## M12 Task 2 — live proof of the ids (25 Oct)

Every run: backup `backups/<run>-original-*` 54/54 SHA-256 verified, PPSSPP closed gracefully, originals 0/54
changed. Screens in `local/m12-shots/steps/`.
- Note on the start state: trials seed from the portable memstick (`local/runtime/.../memstick`, `_1.ppst` of
  8 Oct = stage 21, turn 7), not from the originals. The user played on 24 Oct evening (new S006, originals'
  `_1.ppst`/`_2.ppst`); that only changes the backup reference. A first checkpoint copied from the originals'
  `_1.ppst` loaded the user's city stage (kept as `local/checkpoints/WRONG-city-stage-not-turn7`, unused).
- **Run m12info4 (declaration `info_recon`, new view-only bridge step `info_page`)**: on a third-force unit the
  first Circle shows its move range (red), the second opens the status screen; Right pages Unit -> Pilot.
  Wing Gundam Zero (Quatre, LV36, SP 90) lists **Guard 15, Alert 10, Strike 20, Bless 45** = decoded
  (5,1,15) (3,14,10) (7,27,20) (31,29,45). So **id 3 = Alert, id 5 = Guard** (鉄壁; the code keeps the name
  `Invincible`), 7 = Strike, 31 = Bless. Cross returns to the map.
- **Run m12alert1 (`spirit_cast_recon` Alert on 149303184 = Ptolemaios, from `local/checkpoints/turn7-start`)**:
  Command menu has **5 entries: Move / Attack / Spirit / Retrieve / Info** (Spirit row 2). Spirit opens a
  **pilot screen** (Sumeragi 19, Lasse 33, Feldt 32, Mileina 29); Circle on Sumeragi -> list Alert 15 (row 0,
  "100% Eva., Self · 1 Battle"), Trust 25 (id 15 = Trust). One Circle cast: back on the map (a yellow area
  around the ship), **SP 19 -> 4, mask +0x14 0 -> 0x04 (`Alert` active)** (ram-01/ram-02 decoded with
  `local/m12-tools/decode_pilot_dump.py`). The production cast step skips this ship safely (5 entries, mech not
  in `SPIRIT_ROW_BY_MECH` -> `menu_layout_unknown`); supporting it needs the pilot-screen Circle (later).
