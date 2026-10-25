# M12 Live checkpoint and retries — design (25 Oct 2026; approved by the user in chat, uncommitted)

## Goal

Save a live checkpoint at the start of a player turn, play the turn cycle (M9/M11 turn, M10 End Turn and strict
enemy phase), and when an ally is lost, reload the checkpoint and retry with that ally protected, up to three
retries. Before the live test, extend the spirit policy to Sense > Focus > Alert > Invincible. Advances the long-term
item "Save/load a live checkpoint and retry defeats automatically" (scope: turn 7 -> 8 of the current stage).

## Decisions (user, 25 Oct)

1. Scope: checkpoint + retry only, on turns 7 -> 8. No multi-turn play, no automatic start (later milestones).
2. Defeat = any ally destroyed or lost (today's strict stop: `ally_destroyed` / `unit_lost`, in the enemy phase or
   by a counter in the player turn). The stage's own lose condition is never reached on purpose.
3. Variation between retries (the game replays deterministically, run m11cp4): protect the ally that was lost —
   it neither moves nor attacks, it Standbys. The protected list grows across attempts.
4. Mechanism: save through PPSSPP's window menu (File > Savestate slot > Save state, as on 24 Oct); load by graceful
   close and relaunch with `--state` (`Launcher.prepare(checkpoint=...)`, proven by run m11cp4).
5. Approach 1: agent-driven steps plus a small pure `retry.py` module.
6. Spirits (added before the live test): one spirit per planned attack, the first of Sense > Focus > Alert >
   Invincible that the pilot has learned, can afford and does not already have active. Alert and Invincible exist
   for pilots without Sense/Focus and help the robot survive.

## Reuse check

No external tool plays this game. PPSSPP's debugger WebSocket offers no save-state command as far as the
retained notes show (confirm in Task 1 against the 1.20.4 subscriber list; if one exists it replaces the window-menu
save). Reused: `Launcher.prepare(checkpoint=(path, sha256))` (hash-checked copy into the trial folder, never the
memstick), the protected backup service, M9 `turn_next`/`plan_act`, MVP Standby, M10 `end_turn`/`enemy_phase` and
`enemy-phase-report.json`, M11 `spirits.choose_spirit` and the cast step (SP drop + effect mask). The offline
`VerifiedCheckpointService`/`BattleSupervisor` scaffolding was considered (approach 2) and not chosen: it needs a
save-state backend and would re-wire proven live paths; only its manifest idea is reused.

## Approaches

1. **Agent-driven steps + `retry.py` (chosen).** Same shape as M9-M11: each step is checkable on a screenshot.
2. One Python driver (supervisor) running launch -> play -> close -> relaunch: closer to the final goal, much larger.
3. Retry only from a fixed pre-made checkpoint: cannot change player-turn moves; leaves the live-save item open.

## Design

**D1 Spirits.** `spirits.NAMES` gains the Alert and Invincible ids, `EFFECT_BITS` their mask bits, `PREFERENCE`
becomes `("Sense", "Focus", "Alert", "Invincible")`; `choose_spirit` is unchanged in shape (one spirit). Ids and bits
come from a view-only recon (pilot spirit screens) and one cast recon each; Alert is expected to be the Flash bit
0x04 alone (Sense = Flash + Aim), Invincible is unknown. Policy clause: `use spirits before attacking` (the old
clause stays accepted as an alias). A cast whose SP drop or mask does not match stays `spirit_mismatch` (skip).

**D2 `src/psp_buddy/retry.py` (pure).**
- `Attempt {number, checkpoint, protected, outcome, reason, lost, reports}`; `Ledger {checkpoint manifest,
  attempts, max_retries=3}`.
- `next_step(ledger, outcome)` -> `done` (turn T+1, no loss) | `retry {protected}` (loss, retries left) |
  `give_up` (loss after 3 retries, or a non-loss stop such as `scene_*`, `turn_jump`, `stage_restart`,
  `phase_budget`, `player_phase_unclear`).
- `manifest(state, file_sha256)` and `matches(manifest, state)`: turn, phase start (every ally unmoved), each
  unit's object, HP, EN, tile. Used after save (sanity) and after every relaunch (must match, else `give_up`).
- `retry-report.json`: ledger content; written after each attempt, errors returned, never raised.

**D3 Protected units.** `protected` unit objects through `plan_act` (the ledger yields objects; a name clause
was dropped as unnecessary, 25 Oct). A protected unit gets no input at all: it stays unmoved, which is the
MVP Standby in effect (End Turn answers Yes with unmoved units), `plan_act` returns handover `protected`, and
`TurnLog` counts it as skipped. Node tool validation as for `bosses` (up to 26 objects).

**D4 Checkpoint save (local tool, PowerShell like the screenshot helper).** At turn T start (memory: turn T, every
ally unmoved, no menu): foreground PPSSPP, File > Savestate slot > slot 3, File > Save state, each menu checked on a
window capture. Then the trial's slot file must be new (mtime and SHA-256 changed), be copied to
`local/checkpoints/<run>/` with `manifest.json` (D2), and the original memstick files stay untouched.

**D5 Retry loop (agent).** attempt 1 from the live game -> on a loss: graceful close, `retry.next_step`, fresh
AGENTS.md backup, relaunch with the checkpoint, `matches` -> play with the protected list -> repeat. Done at turn
T+1 with no loss; stop and hand over on `give_up`.

## Failure behaviour

A failed save (no new file, unchanged hash, menu not seen) stops before any play. A relaunch that does not match the
manifest stops. Retries never write to the memstick's `_1.ppst`; every relaunch is preceded by a verified backup and
followed by an originals check at close. Every stop leaves PPSSPP closed or on a known screen with a report.

## Acceptance criteria

1. Red-first unit tests: spirit preference with the four spirits (each fallback, SP short, active), ledger and
   `next_step` (done, retry, cap, non-loss stops), manifest match/mismatch, protected unit -> Standby only, policy
   clauses, report write errors returned.
2. Navigation and node tests for the new arguments.
3. Ruff, strict mypy, pytest (`--basetemp local/...`), node and helper tests pass.
4. Live, protected: Alert and Invincible ids/bits recorded from screens and casts; one run saves a checkpoint live,
   loses an ally (or forces a retry), reloads at least once, matches the manifest and reaches turn 8 — or shows the
   `give_up` path with a correct ledger.
5. Code review (high) without Critical/Important findings.

## Excluded

Turns after 8, multi-turn play, automatic start from the title screen, the in-game Save, save-state hotkeys,
defender choices, the stage lose condition, moving a protected unit to safety.
