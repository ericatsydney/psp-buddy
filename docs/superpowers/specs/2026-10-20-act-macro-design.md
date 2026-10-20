# M5 `act` macro — design (20 Oct 2026, draft for approval)

## Goal

One bridge operation, `act`, executes one tactical instruction for one ally unit:
select it, optionally Move, then optionally Attack with a named weapon on a named
target, confirm with Start and dismiss the result dialog. Every stage is verified from
memory (M1–M4 reads); a screenshot is only the initial map grounding that every press
sequence already requires.

Instruction (request arguments): `{sequence, screen_file, screen_sha256, context:"map",
unit_object, move_to?:[x,y], attack?:{weapon:<name>, target_object:<int>}, commit:<bool>}`.
At least one of `move_to` and `attack`.

## Reuse check

No existing MCP server, plugin or library drives this game; the PPSSPP debugger input
bridge, state/weapon/target/hit reads and verified `goto` already exist in this repo, so
`act` composes them. Nothing external was adopted.

## Approaches

1. **Server-side macro with memory checks (recommended).** A pure module `act.py`
   (testable with a simulated game) drives the presses through a small I/O protocol.
   Safety (budget, declaration, one grounding screenshot) stays in `InfoNavigation`.
2. Agent-side macro: a node script chaining existing screenshot-grounded presses. No new
   verification, needs a screenshot per press, defeats the "memory over screen" goal.
3. Free-form scripted key sequences. Rejected: cannot be verified or bounded.

## Stages and memory checks (all must pass, otherwise stop and report `stage` and `reason`)

| Stage | Inputs | Memory check |
|---|---|---|
| plan | none | unit is a living ally; `move_to` in reachable set (read_state `reachable`, unit unmoved); weapon exists, `usable` and target in `targets_in_range` (with `moved` = move requested) |
| select | `goto` unit tile, circle | cursor == unit tile (verified walk); unit menu open is checked by the next stage |
| move | circle (Move is the first entry for an unmoved unit), `goto` destination, circle | after the first circle the reachable set is centred on the unit (`_centered`); cursor == destination; after confirm unit tile == destination, EN fell, no other unit changed |
| attack menu | circle (Attack is the default entry after a Move) or `down`,circle (second entry when not moved) | weapon-menu row field (u8 `0x08E397A8`, count u8 `0x08E397AA`, entries at `0x08E39790`) readable and count equals the unit's weapon count |
| weapon | `down` × row, circle | row field equals the wanted row (rank of the weapon among non-empty slots) before circle; hover hit read is no longer the idle value afterwards |
| target | `goto`-style walk on the cursor field to the target tile | cursor == target tile; hover hit is 0..100 (not −10000) |
| forecast | circle on the target | hit chance still 0..100. **`commit:false` stops here and returns the forecast (hit %, tile, weapon, ammo/EN)**; the game is left in the forecast screen. |
| fire | Start (only after forecast; `commit:true` runs it straight through) | acting unit EN or ammo decreased by the weapon cost (charged at Start) |
| result | poll, then circle while the unit's action-finished counter is still set (max 6, each followed by a settle) | counter reaches 0 and `counted_as_unmoved` is false; tile unchanged; report HP/EN deltas of all units |

The legality rules reuse `targets.targets_in_range`; unknown, unreadable or contradictory
memory → refuse before any attack input. A press that cannot be confirmed by memory is
never followed by a different kind of press.

## Safety limits

- Declaration `{"unit":"any","actions":["act"]}` (new) enables `act` and nothing else except
  the existing read-only operations; Standby, End Turn, system menu and manual presses stay refused.
- Only ally units (`raw_menu_group_byte` 0) may act, only foes (group 12) may be attacked.
- `act` budget: at most 8 per trial and 120 presses in total, separate from the tap budgets.
- Each `act` needs a fresh map-context screenshot (hash checked, single use).
- Failure after input leaves the game in its current menu: the result carries `stage`,
  `reason`, memory facts, and `needs_screenshot: true`; the session stays usable and no
  automatic back-out beyond one `cross` for a rejected stage that has not confirmed anything.
- Phase safety unchanged: `confirm` only through the staged Start; no Standby/Info/system.

## Interfaces

- `src/psp_buddy/act.py`: `plan_act(...)` (pure legality plan), `run_act(instruction, io)`
  with `ActIO` protocol (`press`, `read_state`, `read_weapons`, `read_cursor`, `read_hit`,
  `read_menu_row`, `sleep`), result dict `{ok, stage, reason, facts, deltas}`.
- `InfoNavigation`: operation `act`, `_check_act`, wiring of existing readers; a new
  `read_menu_row` reader (3 bytes at `0x08E397A8`); `dismiss_result` stays for manual runs.
- `tools/ppsspp_navigation_mcp.mjs`: tool `ppsspp_act`, validation, 125 s deadline.
- `navigation_handoff.py` (local, ignored by Git): `_read_menu_row`, act timeouts.

## Acceptance

1. Unit tests with a simulated game cover happy path (move+attack, attack only,
   move only), every refusal (not ally, not reachable, weapon unusable, target out of
   range, budget, stale screenshot) and every stage failure.
2. Ruff, `mypy --strict src`, node tests pass.
3. Protected live trial (backup first): at least three actions across two units
   (Destiny move + attack, Z Gundam move + attack), memory facts recorded after each stage,
   no unexpected unit change, original saves unchanged afterwards.

## Exclusions / known gaps

Standby, End Turn, healing/spirit commands, damage forecast values, Z page-2 weapons
(rows beyond one page are walked with `down` like any row), will requirements.
Attack-only with an unmoved unit relies on Attack being the second menu entry (Destiny
verified 18 Oct); other units may differ, which the weapon-row check will catch and refuse.
