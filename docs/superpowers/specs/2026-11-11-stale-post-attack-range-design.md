# Stale Move range after a second attack — design

Date: 11 Nov 2026. Status: conflict review complete; D1 and D2 decided by the user, 11 Nov. Phase 1 approved.

## Problem

Runs s2o and s2p both ended with `result:post_attack_move_not_closed` on Wing Gundam Zero's second
attack of a turn. Wing Zero attacks again after a kill (Continue), and its pilot has Hit and Away
(skill 20), so after the first attack the game offers Move / Standby (user, 11 Nov).

Evidence, from the act traces saved in each run's `navigation-mailbox`:

| Run | Attack | Range in memory at the first read after Start | Presses before it | Result |
|---|---|---|---|---|
| s2p | 1st (kill) | 106, not centred; 142 centred after one Circle | 0, then 1 | Standby chosen, bonus action |
| s2p | 2nd | 142 centred, unchanged | 0 | Cross, Down, Circle, 6 polls, stop |
| s2o | 1st (kill) | 136, then 139 centred after one Circle | 0, then 1 | Standby chosen, bonus action |
| s2o | 2nd | 139 centred, unchanged | 0 | Cross, Down, Circle, 6 polls, stop |

The first attack's Hit and Away Move range stays in the map cells. `act._post_attack_move` only looks
at those cells (`act.py:718`), so on the second attack `act.result` takes the leftover for a Move
display before any result page is dismissed. Its Cross, Down, Circle land on the "Get Result" page
(final screenshots `ULJS00460_00044.jpg`, `ULJS00460_00084.jpg`); it then only polls, and stops.

Not known, and not decidable from retained evidence:

- which UI windows are open while a Hit and Away Move range is really displayed (the window pool was
  never recorded there; `screen.py` has no entry for it);
- whether the Move / Standby menu appears again after the second attack.

## Reuse check

Nothing outside the project knows this game's screens. Inside it, `screen.classify` and the
`ui_windows` list in every state read (M15) already tell menus apart; the result loop does not use
them yet.

## Approaches

1. **Record first, then decide (recommended).** Phase 1 adds the screen name and window list to the
   result trace: memory reads only, no change to any press. One protected run on the same save
   reproduces the stop and shows the windows in all three situations (real Move display, leftover
   range under result pages, whatever follows the second attack). Phase 2 is the rule, written from
   that evidence and brought back for approval.
2. Rule now: accept a post-attack Move range only when `screen == "move_range"`. One run fewer, but
   the Hit and Away display may not classify as `move_range`; then a dismiss Circle would be pressed
   while the Move range is up, which may confirm a move.
3. Rule now: ignore a centred range that was already there before Start. Cannot tell a real second
   Move display from the leftover, since the unit has not moved.

## Scope

In: Phase 1 trace fields; one protected live run; the Phase 2 rule as a follow-up decision.
Out: any change to presses in Phase 1; the Continue and dialogue paths; Big O's unopened Move
window (s2p); the debugger freeze.

## Design (Phase 1)

In `act.result`, each trace entry gains `"screen": state.get("screen")` and
`"windows": state.get("ui_windows")`. The stop record keeps the whole trace instead of the last 8
entries (at most a few dozen small entries), because the last 8 were identical polls in both runs.
`turn.TurnLog` copies an act stop's `facts` into the turn entry as `stop_facts`, so the saved turn
report holds the trace (the open s2j item asks for the same thing).

## Failure behaviour

Phase 1 changes no press. A state without `screen` or `ui_windows` records `None`.

## Acceptance criteria

1. Tests: trace entries carry both fields; a stop record carries the full trace; a turn entry for an
   act stop carries `stop_facts`; every existing test passes unchanged.
2. `pytest --basetemp local/pytest-x` (no path argument), local tool tests, `ruff`, `mypy` pass.
3. Live, protected, slot 2 save of 13:27: the run reaches Wing Zero's second attack; the saved turn
   report shows the windows for the first attack's Move display and for the stop. Originals unchanged.
4. Phase 2 proposal written from that evidence, with the rule, its tests and its own live check.

## Phase 1 result and Phase 2 proposal (s2q, 11 Nov) — awaiting approval

Windows seen in Wing Zero's three result traces (`s2q-run-20261111T094544Z/navigation-mailbox`):

| Windows open | What is on screen | Cost range in memory |
|---|---|---|
| Command window only, no root | Hit and Away Move / Standby menu (also after the 2nd attack) | none, or the leftover |
| Command + range window | Move really displayed (after Circle on that menu) | centred |
| none at all | result / Get Result page | leftover stays |
| root only (`no_menu`) | map | leftover stays |

So the leftover range never has the range window. In s2q the 2nd attack killed its target, and the
Continue path pressed Circle through the result page, so the stop did not recur. In s2o/s2p it did not
kill: after Standby the Get Result page (no windows) waited for a Circle and the loop only polled.

Proposed rule for `act.result`, when a state carries `ui_windows` (otherwise today's behaviour):
1. a centred range counts as a Move display only if the range window `0x08E4BF6C` is open;
2. Command window alone, unit still unmoved: the Move / Standby menu, answered Down + Circle;
3. after Standby, no window open and the unit not yet shown as acted: one Circle per read, within
   the existing `RESULT_PRESSES` limit, instead of polling only.
Byte 2 stays out of `_post_attack_move`. Live check: Wing Zero's 2nd attack without a kill.

## Conflict review

`/plan-eng-review`, 11 Nov, read-only, against `docs/features.md`, the open items in
`docs/progress.md`, the touched code and tests, and the AGENTS.md save rules. Report:
`~/.gstack/projects/ericatsydney-psp-buddy/m14-stage33-eng-review-stale-range-20261111.md`. Outside
review not run (it would send project content externally); review log unavailable (`bun` missing).

- **D1, 4 Nov acceptance** (features.md:101, m16-k: an extra Get Result page "read as a stale
  post-attack Move menu"): the same fault. User, 11 Nov: fix it. The acceptance is retired once Phase 2
  is proven live; until then the stop stays a clean handover.
- **D2, approach** (`screen.py:29-37` has no entry for a Hit and Away Move display): user, 11 Nov:
  record first (Approach 1).

No conflict with save protection, the 400-press budget, or the stop-byte rule that
`_post_attack_move` stays cost-only (Phase 1 does not touch it; Phase 2 must keep byte 2 out of it).
