# Fewer cursor moves and battle animations off — design

Status: approved by the user, 1 Nov 2026 (M15 speed-ups).

## Problem

The user saw the cursor step one tile sideways and back to the unit before its menu opened. Cause:
`spirit_cast.cast_before_attack` walks to the unit, opens the Command menu, finds no screen-checked
layout for some mechs (`menu_layout_unknown`, 10-12 times per stage-33 run, e.g. Ptolemaios2), closes
it with Cross and proves the map by the sideways walk (`_on_map`); then the attack reopens the menu.

## Design (approved)

1. A per-run set `InfoNavigation._spirit_skip` (passed as `plan_and_act(spirit_skip=...)`, then
   `cast_before_attack(skip_mechs=...)`) collects mechs whose layout proved unknown; later actions of
   that mech skip the Spirit attempt with no input (`reason: menu_layout_unknown, cached: true`), and
   the press budget reserves no Spirit presses for them.
2. When only the Command menu was open (`menu_layout_unknown`, `command_row_mismatch`), the map is
   proven from memory first: helper `state.screen == "no_menu"` (UI pool) and the cursor on the unit.
   A Cross from that menu cannot start a dialogue. Otherwise, or without a screen reading, the
   sideways walk runs as before.
3. The sideways walk stays after a real cast, after an unconfirmed cast (list open) and after attacks.

## Battle animations (user decision)

The user turns battle animations off in their own game. No runner code. A checkpoint is a save state,
so a new one has to be prepared from a slot saved after the change (prepare.py). The fixed 8 s wait
after Start (`act.ANIMATION_SECONDS`) is kept until a run with animations off shows what the battle
screens do.

## Acceptance criteria

- Unit tests (`tests/unit/test_spirit_cast.py`): memory proof without the walk; walk when no screen
  reading; a mech is not retried in the same run, with no presses.
- All verification commands pass.
- Live stage-33 run: fewer cursor presses per action than fs-s33a, same play, no stall.
