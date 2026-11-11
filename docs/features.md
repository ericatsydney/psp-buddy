# Existing features and standing decisions

Compact register for the new-requirement conflict review (AGENTS.md). One line per
behaviour that a new requirement could break or contradict. Detail and evidence live in
the linked spec, or in [progress history](research/2026-11-08-progress-history.md).
Updated 8 November 2026. Keep each entry to one or two lines; update it when a feature
is added, changed or retired.

Status: **live** = proven in a protected live run; **offline** = tests only;
**decision** = a user rule that must not change without asking.

## Scope and safety (decisions)

- Scope: the runner clears **non-boss** foes, then hands control back; the user fights
  bosses (25 Oct). Retries after a loss are deprioritised (M12 closed early).
- MVP unit commands are Move and Attack, plus Standby and the Spirits Sense/Focus (and
  Alert/Guard ids known). Healing, Supply, Transform and crew changes are excluded.
- Save protection: fresh SHA-256-verified backups of SAVEDATA and PPSSPP_STATE (and the
  portable memstick) before every launch; trials run on copies; originals must be
  unchanged afterwards (AGENTS.md).
- "Slot N" means the project PPSSPP memstick state file `_(N-1)`, not OneDrive (4 Nov).
- Story dialogues are skipped (Circled through) (24 Oct).
- Battle animations are off in the user's own game; the fixed 8 s post-Start wait stays
  until measured (1 Nov).
- The backup gate's 60 s receipt freshness stays unchanged (3 Nov).
- After a handover the helper refuses all input; another round needs a save + relaunch.

## Start-up and launch (M15, live)

- `prepare.py --slot N [--boss NAME]`: copies the slot into a hashed checkpoint and
  manifest, picks the anchor ally (lowest object rule) and decodes the opening screen.
  [spec](superpowers/specs/2026-11-01-real-test-readiness-design.md)
- An unidentified opening screen stops with no press (`unknown_opening_screen`).
- `run.py`: refuses before launch (`no_manifest`, `machine_busy`, ...), launches
  `restart.ps1` detached (WMI), waits for CPU < 35%, checks the checkpoint
  (`checkpoint_mismatch`), backs out, runs the clear loop, writes `m15-report.json`.
- Back-out from memory: UI window pool classifies the screen; one Cross per step, each
  re-read and checked; cap 6; ends with a cursor-walk map proof. `post_move_menu` and
  `spirit_list` have no proven back-out (refused).
- Checkpoints load into trial copies only (hash-checked, never into the memstick).

## Reading the game (live)

- `read_state`: units, terrain, move costs, cursor (pointer [0x08E4EA90]+0x24), turn
  (u16 0x08DF8ADC), UI windows/screen, in one pause.
  [spec](superpowers/specs/2026-10-19-live-state-and-chosen-actions-design.md)
- Effective move (decision 11 Nov, live s2p): stored move + Dash (pilot skill 21: +1, +2 at will
  130+) + 3 for effect bit 0x80; used for the stop-byte limit and foe reach. Main pilot only.
  [spec](superpowers/specs/2026-11-10-effective-move-design.md)
- Weapons (power, range incl. parts, ammo, EN, hit, flags), targets in range
  (Manhattan), hover hit (raw up to 399; 400 = Sense sure hit; -10000 = non-target).
- Foe = menu group // 4 == 3. Damage forecasts are **not** decoded (hit% x power used).
- Command-menu rows from the u32 entry bitmask 8 bytes before each menu slot's count;
  per-mech table is the fallback. Post-move menu slot 0x08E4BEB4 (menu wraps).

## Acting (live)

- `act`: select, Move, Attack, weapon row (by shown power order; MAP weapons never
  chosen; duplicate names need a slot), target, forecast, Start, dismiss result; every
  stage memory-verified. [spec](superpowers/specs/2026-10-20-act-macro-design.md)
- `plan_act`: plans, gates on the forecast (`min_hit`), fires or backs out, logs damage.
  [spec](superpowers/specs/2026-10-21-planner-design.md)
- A failed attack after a move, or a move that lands elsewhere, ends in a verified
  Standby, never with a menu open. Cursor drift re-walks up to 3 times. Exception (decision
  10 Nov): a tile the game refuses stops the run with the Move window open.
- Stop-byte fallback (decision 10 Nov, live s2o-s2p; `range_source` in the turn report): when cost byte 12 is empty, cell byte 2
  supplies tiles, if the Move window is up and all are within the unit's move. Such a unit only
  advances or retreats, never attacks after that move; if neither byte works it is skipped
  `move_range_unreadable`. [spec](superpowers/specs/2026-11-10-stop-tile-move-range-design.md)
- Continue (kill bonus step) and Hit&Away menus are handled.
- Spirits: Sense then Focus cast before attacks when the policy says so; cast verified
  by SP drop + effect mask; multi-pilot mechs pick the first pilot; an unknown menu
  layout skips the cast for that mech for the run.
  [spec](superpowers/specs/2026-10-23-spirit-boss-policy-design.md)

## Turn, enemy phase and clear loop (live)

- `turn_next` picks the next ready ally; End Turn + enemy phase then a new player turn
  in the same helper. [turn](superpowers/specs/2026-10-22-turn-design.md),
  [end turn](superpowers/specs/2026-10-23-end-turn-design.md),
  [clear](superpowers/specs/2026-10-25-nonboss-clear-handover-design.md)
- Budgets per turn: 40 acts, 1000 presses, **400 cursor presses** (decision, 31 Oct);
  `MAX_PLAYER_TURNS = 6`; clear loop 5-turn budget, `MAX_STEPS` 400.
- Bosses: fixed at start; by stage boss list name, or max HP >= 2x foe median, or only the
  names given with `--boss` (then no HP rule). Bosses are attacked only when no non-boss is
  in reach, with the strongest weapon (decision 26 Oct: keep this rule).
- Enemy phase: Eva. when foe hit > 30%, Def. at 100%; each reaction verified and reported.

## Runner policy (decisions, `local/m13-tools/clear_loop.py`)

Text (max 800 chars): cheap weapons below 10%; strongest boss weapons above 0%; target
non-bosses before bosses; use spirits before attacking; hold units without Focus or Sense
on turn 1; advance toward foes when none is in reach; evade when the foe hit rate is above
30%; end moves within reach of at most 2 foes; strongest weapons above 10%; move damaged
units away from foes; defend when the foe hit rate is at least 100%.
[spec](superpowers/specs/2026-11-03-ally-safety-advance-design.md)

- Foe reach = effective move + longest usable range, read once per run (decision 11 Nov);
  ignores terrain/flying (Manhattan); unknown reach blocks moves; attacking from
  the own tile is never reach-limited (accepted).
- The m16-k extra "Get Result" stop is accepted as a handover (4 Nov).

## Handovers (live)

`handover.json` written once, on the map where possible, then input refused:
`cleared`, `ally_lost` / `ally_destroyed` (stop at once; accepted 7 Nov), `turn_budget`
(player-turn limit), `cursor_budget` (mid-turn, before any press; settles a pending
dialogue first), `player_turn_limit`, `debugger_frozen`, `stopped:<reason>`.

## Robustness and speed (live)

- Debugger freeze fallback: 15 s read limit, link check (`cpu.status` 2 x 10 s), resume,
  retry once, else `debugger_frozen` handover; helper op limit 120 s; every request traced
  to `debugger-trace.jsonl`. [spec](superpowers/specs/2026-11-07-debugger-freeze-design.md)
- Press gap: no pause within 0.2 s of a press / 0.1 s of a resume.
- Identity check at most every 30 s (instant handle checks otherwise).
  [spec](superpowers/specs/2026-11-01-faster-reads-design.md)
- Fast screenshots via PPSSPP's own screenshot (ctypes), only with PPSSPP in front.
  [spec](superpowers/specs/2026-11-01-fast-screenshots-design.md)
- Fewer cursor moves: memory map proof after a menu-only back-out.
  [spec](superpowers/specs/2026-11-01-fewer-cursor-moves-design.md)
- Retention (decision 10 Nov, live s2n; replaces 7 Nov): after each launch keep the newest 5
  complete cycles each of verified snapshots, `portable-memstick-*` and `<label>-original-*`.
  Never pruned: runtime archives, the active runtime, 10 Oct first backups, `-original-config-`
  folders, the two `user-evidence` folders local tests read.
  [spec](superpowers/specs/2026-11-10-backup-cycle-retention-design.md)
- PPSSPP may hang on graceful close after a freeze run; force-close only with the user's OK.
- Diagnostic (10 Nov, offline tests only): a Move range `act.centered` refuses is appended to
  `rejected-ranges.jsonl` in the evidence folder (reasons, cost rows, screen, cursor, menu row
  and masks, read move, stop-byte tiles). Memory reads only, no presses, no change to the plan.
- Diagnostic (11 Nov, offline tests only): the act result trace records `screen` and `windows` per
  read; a result stop keeps its whole trace, and the turn report keeps it as `stop_facts`. Reads only.
  [spec](superpowers/specs/2026-11-11-stale-post-attack-range-design.md)
