# M9 Full player turn — design (22 Oct 2026; approved by the user in chat, uncommitted)

## Goal

Play every ready ally once with `plan_and_act`, then stop before End Turn and hand over a turn report.
Advances the long-term items "choose legal actions" and "move and attack automatically" from one unit to a whole turn.

## Decisions (user, 22 Oct)

- Boundary: stop before End Turn. End Turn and the enemy phase are the next milestone (18 Oct End Turn findings in progress.md).
- A unit with nothing attackable is left unmoved and listed as skipped with its reason. No Standby, no advance move.
- Counter-attacks: report only (per-unit HP/EN changes); no counter prediction. The existing heal-threshold handover stays.

## Reuse check

No external tool plays this game. Reused: `plan_and_act` (one unit), `read_state`, `parse_policy`, the mailbox/`InfoNavigation`
operations. Nothing new is sent to the game by M9; it adds selection, bookkeeping and budgets.

## Approaches

1. **Pure `turn.py` plus a `turn_next` read, agent drives the loop (chosen).** Each call stays under the helper's 120 s hard cancel and
   the one-screenshot-per-act rule; logic is unit-testable.
2. A server-side loop in one operation: exceeds the 120 s cancel and the screenshot rule.
3. Agent-only logic: untestable, not repeatable.

## Design

**D1 `src/psp_buddy/turn.py` (pure).**
- `ready_allies(state)`: units with `raw_menu_group_byte == 0`, hp > 0, `counted_as_unmoved`; ordered by Manhattan distance to the nearest
  living foe (group 12), then unit object. No foe alive: ordered by unit object.
- `TurnLog`: `skipped` (unit -> reason), `entries` (one per `plan_act` result), `stopped` (reason or None). `record(unit, result)` classifies:
  `fired` (ok, phase fired); `skipped` for handover reasons `no_target`, `retreat_needed`, `unit_not_ready`, `unit_not_ally`, and for phase `declined`
  (reason kept; `moved` kept); `stop` for phase `failed`, other handovers (`unknown_*`) and `back_out_failed`. Entries keep forecast hit, weapon, target,
  and HP/EN deltas from the outcome.
- `next_unit(state, log)`: `{unit_object, remaining, skipped, done, stopped}`; `done` when no ready ally is outside `skipped`; `stopped` stops it.
- `report(log, state)`: dict with turn number, counts, entries, skipped, remaining units; written as `turn-report.json`.

**D2 `turn_next` operation (read-only).** Mailbox operation `turn_next` (memory only, no screenshot, no input), MCP tool `ppsspp_turn_next` (only `sequence`).
`InfoNavigation` owns one `TurnLog`, records every `plan_act` result into it, and rewrites `turn-report.json` in the evidence folder after each record.

**D3 Budgets.** `MAX_ACTS` 8 -> 40, `MAX_ACT_PRESSES` 150 -> 1000 so a turn fits one trial. Per-act limits (95 s, hard 120 s) unchanged.

**D4 Loop (agent).** `turn_next` -> fresh map screenshot -> `plan_act` (policy text, optional `min_hit`) -> repeat until `done` or `stopped`; a stop or
`stopped` hands over with the report.

## Failure behaviour

Unreadable or contradictory state: `turn_next` returns `stopped` with the reason, no input. A failed `plan_act` stops the loop. A declined Move leaves the
unit moved and the game on the post-move command menu; the next `plan_act` starts from the map after the agent closes it (the report notes it, loop stops
for a human or a later Standby milestone). The act deadline and press budgets still bound every call.

## Acceptance criteria

1. `turn.py` fixture tests: ordering by distance, skip and done logic, stop on failure, third-force and dead units ignored, no foes.
2. A simulated 3-unit turn through `InfoNavigation` (`SimGame`) ends `done` with a correct `turn-report.json`.
3. Budget and validation tests for `turn_next` (bad arguments, node tool schema).
4. Ruff, strict mypy, pytest, node tests and helper tests pass.
5. One live protected run plays turn 7 until `done`, all memory deltas match, stops before End Turn (AGENTS.md backups, graceful close).
6. Independent review has no Critical/Important findings.

## Excluded

End Turn, enemy phase, Standby, advance moves, healing/Spirit, retries/checkpoints, counter prediction, multi-turn play.
