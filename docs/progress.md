# Project progress

Updated 10 November 2026 (Australia/Brisbane). Compacted on 8 Nov: everything before
is kept verbatim in [progress history](research/2026-11-08-progress-history.md).
What already exists, and the user's standing rules, are in [features.md](features.md).
Ticks mean ready in the scope stated; unchecked items may have partial implementation.

## 1. Long-term goal

Play one battle autonomously from an existing save, following your tactical instructions,
with protected progress, up to three checkpoint retries, and handover when needed.
Scope (25 Oct): clear the non-boss foes, then hand control back for the bosses.

- [x] Verified save/state backup service.
- [ ] Start from an in-game save or save state automatically. (Live for PPSSPP save states
  via `prepare.py` + `run.py`; in-game saves not.)
- [ ] Read the complete current battle state automatically. (Live: units, map, cursor, turn,
  weapons, targets in range, hover hit. Not yet: damage forecasts.)
- [ ] Follow tactical instructions and choose legal actions in a live battle. (Live for the
  runner's policy clauses; free-form instructions not.)
- [ ] Move and attack automatically. (Live: planned Move/Attack/Standby with forecast gate.)
- [ ] Handle enemy reactions and recognized decision-free dialogue automatically. (Live:
  Eva./Def., story dialogue skipped; some reactions skipped `hit_unreadable`.)
- [ ] Save/load a live checkpoint and retry defeats automatically. (Deprioritised by the user.)
- [ ] Complete a battle and hand control back safely. (Live: non-boss clear and handovers.)

## 2. Short-term goal — M15 real-test readiness (user priority, 31 Oct)

The user picks any save state, runs one command, and the runner clears the non-boss foes
or hands over cleanly with no manual steps.
[spec](superpowers/specs/2026-11-01-real-test-readiness-design.md),
[plan](superpowers/plans/2026-11-01-real-test-readiness.md)

- [x] P1 Any save state as input (`prepare.py --slot N`, live on 5+ saves).
- [x] P2 Automatic start-up back-out from memory (live, m15s33b).
- [x] P3 Long turns: clean `cursor_budget` handover within the kept 400-press budget.
- [x] P4 One-command launcher (`run.py`, refuses cleanly under load).
- [ ] P5 Unknown menus from memory. (Spirit/Standby rows from the menu bitmask; other
  unknown layouts hand over or skip.)
- [x] P6 Real tests on other saves: stage 33, slot-3 map, sea map (slot 4), three space maps
  (slot 2), 4-7 Nov; results in the history.

## 3. Open items

- [ ] Debugger freeze, two kinds seen (7 Nov): (a) s2e, link alive but `cpu.stepping`
  ignored -> next fix: re-send `cpu.stepping` if the CPU has not stepped within ~1 s;
  (b) s2h, PPSSPP's whole debugger stopped answering (a fresh socket too) -> only a
  clean `debugger_frozen` handover is possible. Also keep more trace files (rotation
  overwrote the first freeze's records).
- [ ] PPSSPP hangs on graceful close after a freeze run (force-close needs the user's OK).
- [ ] Measure a shorter post-Start wait now that animations are off.
- [ ] Task 10 checks (user: later).
- [ ] s2j (10 Nov): `result_not_dismissed` after Start on a melee attack (unit 149300896 ->
  foe 149302976). Six Circles went unanswered, the unit stayed unmoved, the foe survived and
  no damage-log entry was written. Cause not yet known; the stop record dropped its trace.

- [ ] s2k (10 Nov): `no_target` skips are false "nothing to do" results. All 8 (Hyaku Shiki
  twice, Methuss, Tower, Gurren Lagann, Deathscythe Hell, Altron, Li-Brasta) spent all 7 reads
  in `act.range_when_drawn` without `act.centered` accepting the Move range; all 22 accepted
  ranges passed on read 1. Offline replay rules out the 2-foe rule, crowding and terrain.
  s2l (10 Nov, stopped early on purpose, logging live and uncommitted): 4 rejections, all
  Altron/Hyaku Shiki/Deathscythe Hell (twice), each `empty`: Move window open, cursor on the
  unit, row 0 of a 3-entry menu, cost byte 12 zero on every tile. A timed screenshot of
  Deathscythe Hell shows the game drawing a normal centred range. So the unit could move and
  the runner's read misses it. Evidence:
  `local/move-attack-trial-20261017/s2l-run-20261110T033634Z/rejected-ranges.jsonl`.
  s2m (10 Nov, 3 rejected and 4 accepted raw-cell dumps, then dump data and code removed at the
  user's request): cell byte 2 marks the free reachable tiles for every unit and fills in for
  rejected units too (90-101 tiles, all within their move radius; on accepted units it was
  always a subset of the costed tiles). Only byte 12 (cost) stays empty for rejected units.
  Move-window words +0x30, +0x34, +0x40 are 1 on rejected and 0 on accepted; their meaning is
  unknown. Fix implemented 10 Nov (byte 2, move only), offline tests only, uncommitted, live run
  still to do: [spec](superpowers/specs/2026-11-10-stop-tile-move-range-design.md).
- [ ] Backup retention, newest 5 cycles of all three kinds, implemented 10 Nov, offline tests only,
  uncommitted: [spec](superpowers/specs/2026-11-10-backup-cycle-retention-design.md). First clean-up
  run 10 Nov on the user's yes (list in `local/backup-prune-2026-11-10.txt`): 377 of 384 folders
  fully removed, 48 GB freed, kept 5 of each kind re-hashed clean against their manifests, evidence
  tests pass. The other 7 (`act1-5`, `tgt1` x2 originals, 20 Oct) lost their files but keep empty
  read-only folders and a 4.9 KB manifest; each launch retries and records the failure, harmlessly.
  Automatic prune inside a launch ran correctly live in s2n. Test command needs `--basetemp local/...`
  and no path argument, or 9 launch tests fail falsely.
- [ ] s2n (10 Nov, slot 2 saved 13:27, turn 1): no unit used the stop-byte fallback yet. Altron's
  fallback range was valid, and offline replay shows `no_target` was right (40 closer tiles, none
  within the 2-foe limit). Hyaku Shiki was refused `move_range_unreadable`: 90 stop tiles, but its
  read move 6 leaves only 72 free tiles (98 at move 7), so either the move read is short or the marks
  are stale from another unit. The log records only the tile count, so the next run must log the
  tiles and distances. Replay says Hyaku Shiki had 12 safe closer tiles, so it should have advanced.
  The run ended in `debugger_frozen` mid-turn 1 (read unanswered 35 s, not recovered), 8 units
  unplayed, no ally lost. Originals unchanged (OneDrive 56/56, portable 55/55). Evidence:
  `local/move-attack-trial-20261017/s2n-run-20261110T090449Z`.
- [ ] s2o (10 Nov, same save, tile logging added): the stop-byte fallback worked live for the first
  time: Deathscythe Hell moved (19,25) -> (18,24) with an empty cost byte. Hyaku Shiki was still
  refused, and the log settles why: its 90 marks are its own (no mark on its tile, reaching exactly
  7 tiles from it, 19 of them at distance 7) but the read move is 6. So the marks are not stale and
  the read move is one short for this unit. Offline decode (10 Nov): the game adds pilot skill 21
  (+1, or +2 at will 130+) and an effect flag (+3) to the stored move, see
  [effective move](research/2026-11-10-effective-move.md). Fixed 11 Nov (Dash, user-confirmed rule)
  and proven live in s2p below. Still to test on rough terrain. Evidence:
  `local/move-attack-trial-20261017/s2o-run-20261110T100733Z`.
- [ ] s2o stop on turn 2 after 13 attacks, 11 non-boss foes destroyed, 31 left, no ally lost:
  `result:post_attack_move_not_closed` on Wing Zero 149305264 (TwinBusterRifle, second attack that
  turn). The final screenshot shows a "Get Result" window over the map, so it looks like the extra
  Get Result stop accepted as a handover on 4 Nov (features.md); cause not investigated. Originals
  unchanged (OneDrive 56/56, portable 55/55). Recurred in s2p at the same point (Wing Zero's second
  TwinBusterRifle attack of turn 3), so it is now the main thing ending these runs.
  Checked 11 Nov: not a MAP weapon. Wing Zero has two TwinBusterRifles, slot 1 single-target and slot 3
  MAP (will 120); both stops fired slot 1, and the planner never picks MAP weapons. In both runs the
  failing attack was Wing Zero's bonus action after a kill, and its pilot has Hit and Away (skill 20),
  so the cause is likely the post-attack Hit and Away handling on a bonus action. Not yet fixed.
  Cause found 11 Nov from the act traces (s2o, s2p): the first attack's Hit and Away Move range stays
  in memory (142 tiles in s2p, 139 in s2o) and is still there, unchanged, at the first read after the
  second attack's Start. `act.result` takes it for the Move display (`_post_attack_move` is cost-only),
  presses Cross, Down, Circle onto the Get Result page with 0 dismiss presses, then only polls and
  stops. User, 11 Nov: fix it (retires the 4 Nov m16-k acceptance once proven) and record first.
  Phase 1 built 11 Nov, offline tests only, uncommitted: result trace gains `screen` and `windows`,
  stops keep the whole trace, turn entries keep `stop_facts`.
  [spec](superpowers/specs/2026-11-11-stale-post-attack-range-design.md). Next: live run s2q on the
  13:27 save: s2q run 11 Nov. Windows recorded (table and Phase 2 proposal in the spec, awaiting the
  user's approval). The stop did not recur because the 2nd attack killed its target this time.
- [ ] s2q ended `ally_destroyed` in turn 3: Li-Brasta B (149305992) lost, the first ally lost on this
  save. 22 non-boss foes destroyed, 20 left. Cause not investigated; s2p on the same save and code
  path lost none. Originals unchanged (OneDrive 56/56, portable 55/55). Evidence:
  `local/move-attack-trial-20261017/s2q-run-20261111T094544Z`.
- [x] s2p (11 Nov, same 13:27 save, effective move live): Hyaku Shiki and Deathscythe Hell advanced on
  turn 1 from the stop byte (`range_source: stop_byte` in the turn report); Hyaku Shiki read move 7.
  Three turns, 22 non-boss foes destroyed, 20 left, no ally lost. Altron and Methuss had valid
  fallback ranges but nothing safe to move to. Big O on turn 3 was skipped `move_range_unreadable`
  with the command menu up, not the Move window (12 marks within 2 tiles), so the check refused it
  as designed; why its Move window did not open is not known. Originals unchanged (OneDrive 56/56,
  portable 55/55). Evidence: `local/move-attack-trial-20261017/s2p-run-20261111T080730Z`.

## 4. Latest session — 10 Nov

Live run s2j on the user's new slot 2 (coastal land map, Shin Dragon boss, 24 allies, saved
10 Nov 9:39). Back-out needed no presses; turn 1 and its enemy phase passed; on turn 2 five
attacks fired, then the stop above. 8 non-boss foes destroyed, 24 left, no ally lost.
Backups verified (OneDrive 56/56, portable 55/55) and originals unchanged afterwards.
Evidence: `local/move-attack-trial-20261017/s2j-run-20261109T234310Z`,
`local/m15-runs/s2j/m15-report.json`.

The user pressed on by hand after s2j (the game was not stuck) and saved slot 2 again at
10:10. Live run s2k from that save (turn 2, 23 non-boss foes): turns 2 and 3 played, 17 non-boss
foes destroyed, 6 left, no ally lost, clean `cursor_budget` handover mid-turn 3. The melee
stop did not recur, but that unit fired missiles this time, so it was not re-tested.
Backups verified (OneDrive 56/56, portable 55/55) and originals unchanged afterwards.
Evidence: `local/move-attack-trial-20261017/s2k-run-20261110T001217Z`,
`local/m15-runs/s2k/m15-report.json`.

Next step: the user saves slot 2 from the open PPSSPP, then another run clears the last 6
(back up first). Still open: why s2j's melee result was not dismissed (keep the stop's
trace in the report).

## 4a. Previous session — 7 Nov

Live runs s2e-s2i on the user's slot 2 (city map): one map cleared (s2g), the rest ended
in `turn_budget` / `cursor_budget` handovers or one clean `debugger_frozen` (s2h); no ally
lost in any run; retention verified live. Committed as 8e898de.

Next step: fix freeze kind (a) (re-send `cpu.stepping`) and keep more trace files, then a
live run from a fresh slot-2 battle save (back up first).

## 5. Today/session goal — 8 Nov

- [x] Add the new-requirement conflict gate (brainstorm -> spec + plan -> gstack
  `/plan-eng-review` vs existing features -> challenge the user) to AGENTS.md.
- [x] Compact the progress notes into this file, [features.md](features.md) and the history.
