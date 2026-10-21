# M8 Planner with forecast-gated auto-fire — design (21 Oct 2026; draft for user review, uncommitted)

## Goal

From a policy instruction (the existing `parse_policy` clauses) the agent reads the live battle,
chooses one legal Move + Attack for one ready ally, runs it with `ppsspp_act`, and fires automatically
when the forecast agrees with the plan. This is the first step of the long-term items "choose legal
actions" and "move and attack automatically". Speed (M7, about 45 s per fired act) is accepted as is.

## Decisions already made with the user (21 Oct)

- Scope: planner plus damage-forecast decoding (decode is gated, see D1).
- Instruction input: existing policy clauses; no per-turn directives.
- Autonomy: auto-fire after a forecast check (no per-attack approval).

## Reuse check

No external tool plays this game. In the repo: `planner.py`/`policy.py` (offline, built on the strict
`Snapshot`/`Action` model: needs `legal_actions`, validated `predictions`, and hands over on any unknown),
the live reads (`read_state`, `read_weapons`, `read_targets`, `read_hit`) and `act`. Decision: reuse
`parse_policy` and the selection rules (cheap weapon on weak target, strongest on a boss, median
otherwise, retreat/heal threshold) but score live dicts in a new pure module `tactics.py`; adapting the
live data into `Snapshot` would mean fabricating fields the planner then trusts.

## Approaches

1. **`tactics.py` over live reads (recommended).** Pure, testable with fixtures from retained runs.
2. Adapter into `planner.choose_action`: reuses code but needs invented legality/prediction fields.
3. Formula-only damage: unverifiable; used only as a cross-check.

## Design

**D1 Damage (gated investigation, first).** Important fact from the 21 Oct forecast screenshot: the
in-game forecast shows hit chance, HP/EN and counter weapon, **not a damage number**. So there is no
on-screen ground truth for a damage field; truth is the HP change after a hit. Plan: build a table of
(attacker, weapon power, target, terrain, observed HP delta) from retained runs (atk, zatk, act5, spd5
results), fit/validate the formula from weapon power, pilot/mech stats and defense; accept it only if it
reproduces every retained hit exactly; otherwise fall back to expected damage = hit% x weapon power
(ranking only, flagged `damage_model:"power"`). A new live read is only built if a memory field matches.

**D2 `tactics.py` (pure).** Input: state, weapons, targets (per ally), hit chance where known, policy.
Output: one of `{act: {unit_object, move_to?, attack:{weapon, slot?, target_object}}, expect:{hit, ...}}`,
`{wait/standby...}` is excluded, or `{handover, reason}`. Rules: only allies with the action counter set
and alive; weapon must be usable (ammo/EN, P flag when moving, in range from the chosen tile); target
chosen by the policy order (damaged enemies first; boss rules); movement tile = reachable tile from which
the chosen weapon reaches the target, nearest to the current tile; unknown or conflicting data gives handover.

**D3 `plan_and_act`.** One unit per call: plan, `act` with `commit:false` to the forecast, then a gate:
fire only if forecast hit% equals the planned hit% (hover read), target and weapon are as planned, EN/ammo are
enough, and the unit is above the retreat threshold. Otherwise back out (Cross) and report why. After
firing, check the memory deltas (EN/ammo spent, counter cleared, target HP change vs the damage model) and
record them; a model mismatch is reported, not retried.

**D4 Hit chance for planning.** `read_hit` only works in target select, so planning uses `read_targets` for
legality and a per-target hit-chance probe is optional (one hover read per candidate costs about 1 s now).

## Failure behaviour

Unreadable, stale or contradictory reads: no input, a stage and reason. Forecast gate failure: back out and
report. Budget stays per act (95 s). No save is written by tests; any live trial uses AGENTS.md backups and
graceful close.

## Acceptance criteria

1. D1 outcome recorded: either an exact damage formula validated on all retained hits, or the documented fallback.
2. `tactics.py` returns the expected decision on at least 10 fixtures (attack from current tile, move then attack,
   boss weapon rule, cheap weapon rule, retreat threshold, no target, unknown data gives handover, duplicate weapon
   names use slot, moved unit loses non-P weapons, third-force unit is never a target).
3. `plan_and_act` forced-mismatch test: a forecast with a different hit% refuses to fire and backs out.
4. One live protected run: from a policy text only, the agent picks, forecasts and auto-fires one attack; all memory deltas match.
5. Ruff, strict mypy, pytest, node tests and helper tests pass; independent review has no Critical/Important findings.

## Excluded

Multi-unit loop, End Turn, enemy phase, healing/Spirit/Support, retries and checkpoints (later milestones).
