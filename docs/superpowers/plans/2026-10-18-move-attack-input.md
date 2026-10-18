# Move/Attack/Standby input implementation plan

Spec: ../specs/2026-10-18-move-attack-input-design.md (approved, Standby included).

**Approach:** extend `InfoNavigation` (no new class) with an optional per-trial
`declaration`. Without a declaration every action purpose is refused, so Info-only
behaviour is unchanged. Add a non-terminal `observe` operation that saves a raw coherent
memory sample per stage.

## Declaration (file `action-declaration.json` beside the handoff script, read at startup)

`{"unit": "Destiny", "actions": ["move", "standby"] | ["attack"], "destination_tile": [x, y],
"weapon_name": str, "target_name": str}`. Only fields for declared actions are required.

## Rules

- open_move/open_attack need the action declared and `highlighted_entry` Move/Attack.
- confirm_move: context move_range, `destination_tile` equal to the declaration, once.
- select_weapon (arrows/circle): context weapon_list, `weapon_name` equal to declaration.
- select_target (arrows): context target_select.
- confirm_attack: context attack_forecast, `target_name` equal to declaration, once.
- standby_after_move: only after confirm_move, `highlighted_entry` Standby, once.
- Tap budget 24 when a declaration exists. Circle on a declared confirm always needs a
  frame newer than the last input. End Turn/save/load/Spirit are never allowed.
- observe: any context, non-terminal, no tap, saves `stage-NN.json`.

## Tasks

- [ ] Tests then code in `src/psp_buddy/info_navigation.py` (tests/unit/test_action_navigation.py):
  refusal without declaration, wrong tile/weapon/target, duplicate confirm, standby before
  move, budget, observe non-terminal.
- [ ] `navigation_mailbox.py` accepts `observe`; `tools/ppsspp_navigation_mcp.mjs`
  adds purposes/fields and a `ppsspp_observe` tool; update Node test.
- [ ] `navigation_handoff.py`: load declaration, pass to InfoNavigation, implement observe.
- [ ] Verification: `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp
  local/pytest-<id>`, `ruff check .`, `mypy src/psp_buddy`, `node --test tests/node/*.test.mjs`.
- [ ] Independent review; fix Critical/Important findings. No live trial until cleared
  and the user is told. Nothing committed.
