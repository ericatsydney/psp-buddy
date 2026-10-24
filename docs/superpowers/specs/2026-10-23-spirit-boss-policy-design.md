# M11 Turn-7 policy: Spirits and non-boss targets first — design (23 Oct 2026; approved by the user in chat, uncommitted)

## Goal

Raise hit rate, cut damage taken and clear the map faster in the M9 player turn, so the turn-7 play no longer leaves allies
(Gundam 00, Shenlong) fragile and the M10 enemy phase can reach turn 8. Advances the long-term items "follow tactical
instructions" and "handle enemy reactions".

## Decisions (user, 23 Oct)

1. Spirit rule: every unit with a planned attack casts **Sense first**, **Focus** if Sense is not learned or not
   affordable, otherwise none. No SP reserve.
2. Target order: **non-boss foes before bosses**; within each group the existing order (damaged before undamaged, lowest HP
   fraction, nearest).
3. Bosses: a foe is a boss if its mech name is in the boss-name list (default Mercurius, Vayeate, Wing Gundam Zero) **or**
   its max HP is at least 2x the median max HP of living foes.

Assumed game meaning (not verified, user may correct): Sense = the next attack hits and the next enemy attack misses once;
Focus = about +30% hit and evasion until the turn ends (covers the enemy phase).

## Reuse check

No external tool automates this game. Reused: `tactics.plan_attack` (targets, weapons, `bosses` already passed in for the
weapon rule), `plan_act.plan_and_act`, the `act` macro stages and their memory checks, `turn_next`, the screenshot/mailbox
gate, the pilot SP field (`reader`, `max_sp`/`sp`), the mech-name decoder (`weapons.decode_name`), `ppsspp_dump_ram`.
Known: the command menu lists Move / Attack / Spirit / Info (10 Oct, 17 Oct); Setsuna's pilot screen shows Focus 15,
Sense 20, Yell 35 SP (10 Oct capture).

## Approaches

1. **Always cast before acting (chosen):** simple, also protects the unit in the enemy phase.
2. Only when the forecast hit is low: saves SP, but costs a forecast look, back-out and re-entry (about 45 s per unit).
3. Only for weak units: protects the fragile ones only; does not help hit rate.

## Unknowns (resolved by step 1, a view-only recon)

Spirit menu layout and entry order; whether a pilot selection appears (multi-pilot units); where each pilot's spirit list
and costs live in memory; whether casting shows a Yes/No confirmation; a memory signal for an active Sense/Focus.

## Design

**D0 View-only Spirit recon (new declaration `spirit_recon`).** Bridge purposes:
- `open_spirit` (Circle, context `unit_commands`, `highlighted_entry` "Spirit");
- `spirit_pilot` (Circle, context `spirit_pilots`) — only opens a pilot's spirit list;
- `spirit_menu_move` (directions, contexts `spirit_pilots`, `spirit_list`);
- `cancel` also from `spirit_pilots`, `spirit_list`.
No Circle is accepted in `spirit_list` (it could cast). Every other battle purpose is refused in this trial. RAM dumps on the
command menu, pilot screen and spirit list feed the offline decode of spirit lists, costs and the active-effect field.

**D1 Bosses and target order (`tactics`, pure).**
- `boss_objects(state, names, factor=2)`: living foes whose decoded mech name is in `names` or whose `max_hp >= factor x`
  median foe `max_hp`. Needs mech names in the state (added to `read_state` units if not already present).
- `_plan` sort key gains a leading `is_boss` term when the policy says so. Weapon rule unchanged.
- Policy clause `target non-bosses before bosses` (fixed clause); default list of names via `ppsspp_plan_act` /
  `turn_next` argument `boss_names` (max 8 strings, 32 chars).

**D2 Spirit choice (`spirits.py`, pure).** `choose_spirit(pilots)` over decoded `{name, sp, spirits: [{name, cost}],
active}`: first pilot with Sense affordable and not active -> Sense; else first with Focus affordable and not active ->
Focus; else none. Returns `{pilot_index, spirit, cost, row}` with the menu row taken from the decoded list order.

**D3 Spirit step (`act`, before Move).** Command menu -> Spirit -> (pilot) -> row -> Circle -> (Yes if a confirmation
exists) -> back to the command menu. Confirmed when that pilot's SP fell by exactly `cost` (and the active field, if
decoded, is set). Policy clause `use sense then focus before attacking`. Only for a unit whose plan has an attack.

## Failure behaviour

A refusal is a `NavigationRefused` before input. A Spirit stage that does not confirm backs out with Cross to the command
menu (memory-checked) and the act continues without a Spirit, reporting `spirit: "skipped"` with a reason; it never stops
the turn. An SP drop that does not match the cost stops the act as `spirit_mismatch` (something unexpected was cast).
Budgets: 6 presses and 20 s per Spirit step; time guard like the Standby guard.

## Acceptance criteria

1. Recon: menu screens captured, spirit list order and costs decoded for at least one pilot with Sense and Focus, nothing
   cast, PPSSPP closed gracefully, originals unchanged.
2. Unit tests (red first): boss detection by name and by HP, non-boss-first order, spirit choice (Sense, Focus fallback,
   SP short, already active), bridge refusals for `spirit_recon` and the cast step.
3. Live turn 7 played to `done`: every unit with a planned attack and an affordable Sense/Focus cast it (SP drop
   verified); non-bosses attacked before bosses.
4. Strict M10 run reaches turn 8 without losing an ally, or the loss is reported (never accepted).
5. ruff, strict mypy, pytest, node tests, helper tests pass; code review (high) with Critical/Important fixed.

## Exclusions

Other spirits (Yell, Trust, etc.), SP reserve, spirits on units that only Stand by, enemy-phase defender choices.
