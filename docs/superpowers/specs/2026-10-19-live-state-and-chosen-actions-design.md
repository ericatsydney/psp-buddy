# Live battle-state reading and agent-chosen Move/Attack

Status: draft for user review (nothing implemented). Builds on the working agent input bridge,
`ppsspp_dump_ram`, `ppsspp_observe` and the 18-19 October findings.

## Goal

From one tactical instruction (for example "attack the nearest enemy with Z Gundam"), the agent
reads the live battle state, chooses a legal Move and Attack itself, executes it, and verifies the
result against memory, with no human input and few screenshots.

## Scope and exclusions

In: reading units, terrain, turn, cursor and reachable tiles; choosing and executing Move, Attack,
Standby; result-box dismissal; End Turn and enemy-phase advance (already working).
Out: Spirit, Supply, Morph, crew changes, save/load, checkpoint retry, multi-turn planning, enemy-phase
decisions beyond pressing Start on the default. Original saves are never written (trial copy only).

## What we already know (evidence)

Unit rows (tile, HP, EN, counter), map 24x34 and cell table at 0x08E4EA94 (byte 0 = terrain: 1 space,
2 asteroid, 18 debris; byte 12 = move cost while a range is shown), turn counter u16 at 0x08DF8ADC,
hover hit chance at 0x08ED055C/0560 (-10000 = no target), weapon-list index at 0x08E397A8 (candidate).
Unknown: cursor tile, active menu/context, weapon table (names, range, ammo, flags), damage forecast,
terrain cost for other unit types.

## Approaches

1. Recommended: memory-first closed loop. Find the cursor tile and menu state in RAM, add a small
   `read_state` bridge operation (rows + cell table + turn + cursor, no 24 MB dump), and build
   macro actions that move the cursor, press buttons and verify by memory, using screenshots only
   for ambiguity. Planner stays with the agent (no heuristic code yet).
2. Screenshot-only loop with better macros: no new reverse engineering, but still slow and fragile.
3. Full automatic planner first: too much unknown state (weapon table, damage) to be reliable.

## Interfaces

- `read_state` (new bridge op): returns `{turn, cursor_tile, units[], terrain_rows, reachable (if a move range
  is displayed), hover_hit}`; hash-referenced file for the full cell table; no input.
- Macros (new MCP tools, each bound to the declaration allowlist): `goto_tile`, `select_unit`,
  `probe_move_range`, `probe_weapons`, `act` (select, move to destination, weapon, target, Start, dismiss).
- Every macro verifies by memory after each step and stops on any mismatch; irreversible steps still
  need the declaration (unit, destination, weapon, target) and a fresh frame.

## Failure behaviour

Unexpected cursor/context stops the macro and returns the raw state; transport errors stay terminal;
refusals before input stay non-fatal. No retry of a confirmed action.

## Acceptance

1. Cursor tile and context read correctly from memory in at least 20 sampled states.
2. `goto_tile` reaches 10 random tiles with no screenshot.
3. Reachable tiles read from memory equal the on-screen overlay for two different units.
4. Given an instruction, the agent selects a legal destination and target from `read_state`, executes
   `act`, and the result matches the forecast hit/HP/EN changes, for at least three actions across two units.
5. All unit tests, Ruff, strict mypy, Node tests, independent review pass; protected backups for every trial.
