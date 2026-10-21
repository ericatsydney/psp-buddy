# Speed milestone (M7) — design (21 Oct 2026, approved by the user; uncommitted)

## Goal

Cut one unit action (Move + Attack, fired, result dismissed) from about 70 s to the
forecast and 90-100 s to fire, to **under 30 s end to end**, without weakening
memory verification of the outcome. This precedes the planner/auto-fire milestone
(see "Next milestone").

## Requirements (user answers, 21 Oct)

- Target: under 30 s per unit action.
- Fresh-frame screenshot gate: may be **relaxed broadly** (screenshots at the start and on
  a failed check; the pre-fire forecast screenshot is optional once damage/hit are read from memory).
- Damage forecast: investigate a memory field first; formula only as a ranking cross-check.

## Reuse check

No external tool applies; the cost is inside this repo's read path (`read_state`,
`read_weapons`, `read_hit`, `act_read`, 14-19 s per state read) and the fresh-frame gate
(about 2.5 s per input). Existing `act.py` stages and verified field bindings are reused.

## Approaches considered

1. **Profile, then lean reads (step 1).** Measure where 14-19 s goes (collector, debugger
   round trips, code fingerprint checks); add narrow reads. No safety change.
2. **Memory-verified input pipeline (step 2, recommended with 1).** Presses go back to back;
   each is allowed only after the previous step's memory check passed; screenshots at the start
   and on failure. Needed to reach 30 s. Risk: a wrong blind press is caught only after the fact.
3. **Damage decode (side investigation).** Offline dump search for the forecast numbers, one
   live view-only check. Gated; fallback is the screenshot, then hit% only.

## Design

**S1 Profile (no code change to behaviour).** Aggregate the `act_read` log (seconds per read
by kind) and time one state read's internal steps. Output: a table in
`docs/research/2026-10-21-read-profile.md`. Stop condition: cause of the 14-19 s identified.

**S2 Lean reads.** New narrow reads, each memory-only and verified against the full read:
`read_actor(unit_object)` (tile, HP, EN, ammo, action counter), `read_cursor_and_row`
(cursor tile, weapon-menu row/count, hit pair in one call). Full `read_state` once per action
(planning); the fire poll uses `read_actor`. Target per narrow read: under 3 s (to be confirmed by S1).

**S3 Pipeline.** `act` stages send their presses without waiting for a new frame when the
preceding memory check passed; a failed or unreadable check stops the run (existing Cross
back-out) and the next action starts from a screenshot. First press of each action still needs one
fresh grounding screenshot. Existing budgets (presses, 95 s) stay; the time budget drops with the target.

**S4 Damage decode (gated).** Offline search of retained dumps (wrec, zrec, atk, zatk, act runs)
for the forecast values. If a field matches the screen in at least 3 weapon/target pairs, add
`ppsspp_read_forecast` (hit, damage, counter) and make the pre-fire screenshot optional.
Otherwise record the negative finding and keep the screenshot.

## Failure behaviour

Any unreadable, stale or contradictory read sends no further input, reports `stage` and `reason`,
and falls back to screenshot mode. A hard cancel mid-read is never used (it wedged the emulator
in the act1-act4 runs); stop cooperatively. No save is written by tests.

## Acceptance criteria

1. S1 table committed to docs (uncommitted in git until asked) identifying the dominant read cost.
2. Narrow reads equal the corresponding full-read fields on at least 3 live units (Destiny, Z Gundam, one foe).
3. A live protected act (move + attack, fired) completes in **under 30 s** wall time, every outcome
   fact verified from memory, twice (Destiny, Z Gundam).
4. A forced check failure (e.g. wrong declared row) stops without further input and reports the stage.
5. S4 either meets its 3-pair rule or records the negative result.
6. Ruff, strict mypy, pytest, node tests and helper tests pass; independent review has no
   Critical/Important findings.

## Excluded

Planner, policy-driven choice, multi-unit turn loop, End Turn, enemy phase.

## Next milestone

Planner + auto-fire (user-approved scope on 21 Oct): `tactics.py` over live reads and `parse_policy`
clauses, forecast gate (hit%/damage match) before Start, one unit per call.
