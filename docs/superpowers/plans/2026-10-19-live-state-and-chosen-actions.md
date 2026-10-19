# Live state and chosen actions implementation plan

Spec: ../specs/2026-10-19-live-state-and-chosen-actions-design.md. Tasks are bounded; each ends with
checks (`.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp local/pytest-<id>`,
`ruff check .`, `mypy src/psp_buddy`, `node --test tests/node/*.test.mjs`). Nothing is committed
until the user asks. Every live trial uses fresh verified backups.

## Milestones

- [~] M1 (done with limits, 19 Oct) Cursor and context from memory (offline first). Using the ~40 retained dumps with known cursor
  tiles and screens, diff for the cursor tile (u16 pairs equal to the known tile in each dump) and the
  active menu/context (command menu index, weapon index, system menu). Output: addresses plus a
  verification script. Exit: correct in at least 20 sampled states, a held-out set included.
- [~] M2 (offline complete 19 Oct, live check pending) `read_state` operation. TDD in `src/psp_buddy` (state decoder with synthetic fixtures), mailbox/MCP
  tool `ppsspp_read_state`, handoff reads rows, turn, cursor and the 0x4000-byte cell table in one pause.
  Exit: matches the retained observation for units and the cell table dump byte for byte.
- [ ] M3 Macros without screenshots. `goto_tile` (cursor navigation closed loop), `select_unit`,
  `probe_move_range` (open Move, read cost field, cancel), with memory verification after each press.
  Exit: acceptance 2 and 3.
- [ ] M4 Weapon and target probing. Locate the weapon table (names/range/ammo/flags) in RAM or keep the
  agent reading the screen where not found; `probe_weapons`, hover hit chance from memory.
  Exit: availability rule (ammo/EN, P flag, target in range) checked against three units.
- [ ] M5 `act` macro and instruction following. Declaration generated per action, execution with memory
  verification, result dismissal; run live on at least three actions across two units.
- [ ] M6 Review, docs and handover notes; independent review fixes; update `docs/progress.md`.

## Sequence and risks

M1 first (no emulator needed). Risks: cursor field not found (fallback: keep one screenshot per step),
weapon table not found (fallback: screen reading), terrain costs for other unit types (probe live, do not
assume). Each live trial: close PPSSPP, back up SYSTEM plus launcher snapshots, new evidence directory.

## M1 result (19 Oct, offline on 19 retained dumps)

- Cursor tile: u16 x at 0x096007C4 and u16 y at 0x096007C6 is the only address pair consistent in all 18 labelled dumps (6 distinct
  tiles, 5 contexts, 4 sessions). Held-out check is still outstanding (no ground truth exists for the two unlabelled dumps) and moves to
  M3 (`goto_tile` closed loop must reach 10 random tiles).
- Menu struct near 0x08E39780: u8 highlighted index at 0x08E397A8 and u16 item count at 0x08E397AA (weapon list: index 0..4, count 5 for
  Destiny, 7 for Z Gundam); the command ids list sits just before. The system menu and map states keep the previous values (stale), so
  these fields identify a weapon list but not "system menu vs map".
- No single memory field separates map / weapon list / target select / system menu / move range: every address that did was inside
  UI/render buffers (0x08CE6xxx-0x08CE7xxx). The retained dumps do not cover the unit command menu, forecast, dialogs or result box.
- Decision: context is derived from composite signals (menu struct, hover hit field, move-cost cells present, cursor tile) plus one
  screenshot at each context transition; a labelled context dataset (about 20 dumps in two trials) is deferred and only worth collecting if
  screenshots prove too slow in M3.

## M2 result (19 Oct, offline)

- `src/psp_buddy/battle_state.py` (pure decoders: terrain/cost rows, reachable tiles, cursor, turn; strict bounds), bridge operation
  `state` (takes only a sequence, no screenshot, max 200 per trial, refusals consume neither sequence nor budget), MCP tool
  `ppsspp_read_state`, handoff `_read_state` (units from the coherent observer, then one short pause reading dimensions, cell table,
  cursor, turn; never a RAM dump; response capped at 15 000 bytes, `reachable` dropped first when large).
- Checked offline against the retained Move-range dump: 24x34, classes space/asteroid/debris, 69 reachable tiles (max cost 6), cursor
  (18,13), turn 7, about 2 KB of JSON. Tests: 1199 Python, 175 helper, 8 Node, Ruff, strict mypy. Independent review: two Important
  findings (oversized response and transient bad map killing the session) fixed with tests.
- Known limits: units and map are two short reads, not one atomic snapshot; `reachable` is non-empty only while a Move range is shown
  but stale cost bytes outside that display are not flagged; running_total is not range-checked.
- Live check (needs a protected trial): `ppsspp_read_state` on the real emulator, compared with a screenshot and a RAM dump in the same state.
