# PSP Buddy: autonomous battle MVP

Date: 10 October 2026

Status: written specification approved by the user on 10 October 2026

Target: Super Robot Wars Z2 Rebirth, English v0.8, game ID ULJS00460

Emulator: portable Windows x64 PPSSPP v1.20.4

## 1. Outcome and scope

Run one battle map from a user-selected save state using local tactical rules. Preserve allied robots, checkpoint progress in one save-state slot, retry failed enemy phases with different reactions, and return control to the user at map completion or when assistance is required.

The MVP includes dialogue skipping within the selected map. It stops at the map-clear transition before choosing routes, upgrades, deployments, or the next map. Campaign progression remains a later feature.

The user supplies their own emulator, patched game, and saves. None of these assets, private snapshots, backups, or secrets are distributed with the repository.

## 2. Evidence and remaining integration work

Protected investigations established:

- Portable v1.20.4 loaded a copied slot-2 state and returned the same checked HP/EN values as v1.9.3.
- The user confirmed normal in-game saves loaded through the game menu in v1.20.4.
- A direct API right-button press completed and the user confirmed the cursor moved exactly one tile.
- Candidate current HP/EN fields for Gundam 00 and Shenlong survived a same-state restart. Other maps and arbitrary saves have not been validated.
- Original saves and emulator settings were hash-checked and unchanged during the trials.

These checks establish compatibility of the tested saves and a usable input primitive, not a complete game reader or runner. Maximum HP, full roster iteration, affiliation, positions, action status, SP, healing, weapons, attack predictions, defeat, and map completion still require validation. The v1.20.4 Direct3D11 screenshot and render-buffer calls failed; native capture also timed out. Screen confirmation must have a validated capture path before autonomous menus are enabled.

Research details and candidate addresses are in [the feasibility record](../../research/2026-10-10-hybrid-feasibility.md). Candidate addresses are investigation evidence, not production constants.

## 3. Starting and configuring a run

The user chooses an existing battle state and one working checkpoint slot; slot 2 is the initial test fixture. The runner verifies the emulator version, game identity, decoded state, backup manifest, and effective rule settings before issuing inputs. It never guesses a slot or silently loads another game.

The supplied state is the initial checkpoint. Every later checkpoint replaces that same slot. Immutable pre-run backups remain separate from this one working checkpoint and are never rotated away.

The MVP accepts natural-language instructions for its supported rules and converts them once into a validated local configuration. A bounded local parser supports the documented healing thresholds, reaction priorities, enemy/weapon policy, retry limit, and stop conditions. Unsupported or contradictory instructions are reported before execution; they are not silently ignored. Display the interpreted settings for review. Open-ended tactical reasoning and model calls during combat are outside the MVP.

The portable emulator uses its own writable memory stick populated with copies of user saves/settings. The runner validates its effective paths before testing. It never automatically copies trial saves back into the original memory stick.

## 4. Architecture and interfaces

Use a local Python application with a command-line entry point and structured configuration, observations, and event logs. The implementation plan will name exact modules and commands. Components have separate responsibilities:

| Component | Responsibility and interface |
| --- | --- |
| Backup service | `prepare_trial()` copies and verifies required directories; returns a manifest or blocks the trial. |
| Emulator adapter | Connects to the local debugger; reads memory/status, issues bounded button commands, and manages brief observation pauses. |
| Game reader | `observe()` decodes a coherent, validated game snapshot tied to the patched game profile and current state. |
| Screen recognizer | Identifies the current menu/dialogue/confirmation screen through validated local capture and recognition. |
| Rule interpreter | Converts supported natural-language settings into explicit, validated policy configuration. |
| Tactical planner | `choose_action(snapshot, policy)` selects only currently legal actions without sending inputs. |
| Action executor | Performs an action through bounded input sequences and verifies its resulting state before continuing. |
| Checkpoint manager | Saves/loads the selected slot through verified PPSSPP features; confirms completion and checkpoint identity. |
| Safety supervisor | Tracks allied losses, uncertainty, retries, timeouts, stop requests, and handover. |

Data flow: backup and startup validation -> observation -> safety checks -> local decision -> input execution -> verified new observation. Checkpoint save/load has its own explicit completion checks. An API acknowledgment alone is not proof that the intended game action happened.

The adapter is restricted to observations, controller input, execution control, and existing save-state features. It does not write game RAM, registers, cheats, or gameplay statistics. Ordinary bulk reads use the debugger API rather than process-memory access.

## 5. Observation contract

Each snapshot identifies the game/map, turn and phase, active menu, cursor, and deployed units. Unit observations include stable identity/type, affiliation, position, HP/max HP, EN, pilot identity/level/stats/SP, action availability, and capabilities. Weapon observations include resource costs, ammunition, power, range, movement restrictions, target legality, and applicable combat predictions.

Validate bounds and internal consistency, including positive maximum HP, current HP within range, valid coordinates, known affiliations, and legal menu transitions. Track scripted departures and reinforcements separately from confirmed defeat. Unit disappearance alone is insufficient evidence of defeat.

Only make a decision when its required fields are validated and current. Use a verified game preview or a calibrated local estimate for damage/survival comparisons, accounting for the target's defenses and relevant combat modifiers. Estimates are not guarantees. If a required prediction or field is unavailable, hand over rather than inventing it.

Memory profiles are keyed to the tested game/patch identity and validated at runtime. Do not use temporary stack copies as persistent unit records. Confirm record identity and layout across different units, map phases, and reloads.

## 6. Player-turn strategy

### Healing and retreat

For every live ally, compute current HP / maximum HP. Below 70%:

1. Prefer Repair if a live repair-capable ally with an available action can legally reach and repair the target this turn. Schedule the repairer so an earlier attack does not consume that action.
2. Otherwise use Trust from an eligible pilot with sufficient SP and a legal target.
3. Reobserve after healing. If the robot remains below 70%, reevaluate available healing without repeating an ineffective action indefinitely.
4. If neither healing option is available, avoid attacking and retreat. Prefer a legal destination outside enemy attack reach; otherwise minimize exposure and maximize distance from the closest enemy. If no legal move improves safety, remain in place without attacking.

At exactly 70% HP the healing rule does not trigger. Never move a defeated or unavailable healer, spend nonexistent SP, or select an unusable command.

### Enemy selection

Consider legal targets reachable by a permitted move-and-attack this turn. Prioritize damaged enemies over undamaged enemies. Within those groups, prefer enemies expected to be destroyed by an available attack, then lower remaining HP percentage. Use distance and stable unit identity as tie-breakers.

When no attack is legal, move toward the preferred enemy if doing so respects the robot's healing/retreat rule. Reobserve before attacking. Do not pursue an unreachable target by issuing invalid moves, or end the turn while usable actions remain simply because every unit was visited once.

### Boss heuristic

Count currently deployed enemies by robot type:

- A type with more than three instances is normal.
- For rarer types, compare maximum HP and defense with the common-enemy baseline. The baseline is the median maximum HP and median defense of deployed enemy instances belonging to types with more than three instances.
- A rarer enemy is a likely boss only when both maximum HP and defense exceed those baselines.
- If there is no baseline, a required stat is unknown, or indicators conflict, classify the enemy as non-boss.

This deliberately simple heuristic is configurable and is not a claim of canonical game boss identity. Boss classification affects weapon choice; it does not replace the damaged-enemy target priority.

### Weapon choice

Filter to weapons legal against the selected target and affordable with current EN/ammunition. Evaluate target defenses through the available validated combat data.

| Target condition | Selection |
| --- | --- |
| Non-boss with less than 20% HP | Lowest resource-cost legal weapon. |
| Boss with more than 90% HP | Legal weapon with highest target-adjusted estimated damage. |
| Every other case | Medium-strength legal weapon. |

For a deterministic default, compare resource cost as the fraction of remaining EN consumed plus the fraction of the selected weapon's remaining ammunition consumed; a resource the weapon does not use contributes zero. Break equal cost by greater estimated damage, then stable weapon identity. This makes EN/ammo comparison explicit rather than assuming they are interchangeable raw numbers.

Define medium strength as the median candidate after sorting by target-adjusted estimated damage; choose the lower median when there are an even number of candidates. With one legal weapon, use that weapon. At exactly 20% or 90% HP, use the middle-case rule. If no weapon is legal, choose movement/wait rather than forcing an attack. MAP weapons and attacks that risk allied damage are excluded from the MVP.

## 7. Enemy-phase reactions and retries

On the initial attempt, evaluate each incoming attack in this order:

1. Defend when enemy hit rate is greater than 80%.
2. Otherwise evade when allied HP is below 50%.
3. Otherwise counterattack if legal; if no counterattack is legal, defend.

Exactly 80% does not trigger the first rule; exactly 50% does not trigger the second. Read the prediction before committing a reaction and verify the resulting battle state afterward.

If any allied robot is confirmed defeated, stop further battle input, do not overwrite the checkpoint, and reload the last verified state in the same slot. Count a retry only after a successful reload starts a new attempt. Keep the retry counter in runner state so loading a game state cannot reset it.

Allow at most three reload-and-retry attempts after the initial attempt: four attempts total per checkpoint. Reset the counter only after the enemy phase finishes with no allied defeat.

Retries may override all normal reaction priorities to keep allies alive. Generate bounded, deterministic alternatives using defense-heavy, evasion-heavy, and mixed survival strategies, informed by observed failed attacks and valid predictions. Record reactions by allied identity and incoming attack context; avoid replaying a previously failed identical sequence when an alternative exists. Counterattacks remain eligible when they offer the best estimated survival outcome.

The checkpoint is saved after allied actions, so retries cannot change movement, healing, or attacks already represented in it. If no distinct legal reaction alternative remains, hand over early. After the third retry fails, hand over without a fourth reload.

## 8. Checkpoint lifecycle

Use only the selected working slot. At the end of a player turn:

1. Reobserve and verify no allied defeat, the expected phase, and completion of all legal actions or deliberate waits.
2. Save into the same slot through an existing PPSSPP save-state mechanism.
3. Confirm successful completion, correct slot/game, and a valid updated state before ending the turn. Merely seeing a changed modification time is insufficient.
4. End the turn and enter enemy-phase monitoring.

Do not end the turn if checkpoint saving fails. Do not save while an attack, dialogue transition, defeat, or unresolved menu is active. Preserve the previous verified checkpoint on failure as far as PPSSPP's supported save/undo behavior allows; the immutable backup is the ultimate recovery source. Never automatically restore or overwrite normal in-game BIN saves as part of a retry.

Save/load controls are an integration gate: direct controller input does not itself prove access to emulator save-state menus. Investigate and verify the supported mechanism before enabling checkpoint writes.

## 9. Safety, control, and handover

Hand over on map completion, exhausted retries, unresolved observation, unexpected choice/transition, invalid state, repeated lack of progress, connection loss, failed save/load, or a user stop request. Provide the reason, current checkpoint, retry count, affected units, and a concise action history. Do not automatically enter another map.

Skip only recognized dialogue that requires no decision. Route choices, deployment selection, unfamiliar prompts, and completion screens require handover. Bosses with ambiguous classification remain non-boss rather than causing a stop solely for that reason.

Use bounded timeouts and action budgets. A button operation uses an explicit short duration and release cleanup; stop sending actions when its outcome is unknown. Brief observation pauses resume in cleanup during normal operation. For an intentional safety handover, release injected buttons, clearly state whether the game is paused, and give the user a way to resume manually. Do not silently leave joystick control blocked.

Keep diagnostics local and excluded from Git. No model calls per frame, per action, or per retry. A live runner must not depend on this chat remaining active.

## 10. Save protection and public repository hygiene

Before every emulator trial, create a fresh timestamped, immutable backup of the complete original SAVEDATA and PPSSPP_STATE directories and the active portable memory stick's save directories if present. Back up configuration before changes. Include BIN files, metadata, images, state files, and undo states. Verify every copied file against the source using SHA-256 and retain a manifest.

Copy while PPSSPP is closed or confirmed not to be writing saves. Any missing directory, copy failure, hash mismatch, or uncertain write state blocks the trial. Preserve every earlier backup. Verify original files remain unchanged after isolated trials.

Ignore backups, portable emulator binaries, game images, private snapshots, logs, secrets, and generated output. Keep machine-specific paths in local configuration. Do not commit, push, merge, or publish without the user's authorization for that action.

## 11. Validation and delivery gates

1. **Observation and transport:** establish reliable capture/menu recognition; validate roster, resource, phase, position, weapon, combat, defeat, and completion fields. Confirm direct inputs and releases against game state.
2. **Save/load:** use copied saves to verify normal loading, the chosen state's compatibility, same-slot checkpoint creation, completion detection, and reload restoration. Preserve source hashes.
3. **Local rules:** test the approved strategy using synthetic/recorded observations without launching PPSSPP.
4. **Executor and supervisor:** test legal menu flows, uncertain outcomes, connection failure, timeouts, stop requests, and retry accounting.
5. **Protected battle:** run one selected map only after earlier gates pass, with a fresh verified backup and user-reviewed settings.

Acceptance checks include:

- Threshold boundaries at 70%, 50%, 20%, 90%, and enemy hit rate 80%.
- Damaged-target priority, boss ambiguity fallback, and deterministic weapon selection.
- Repair reachability/action reservation, Trust SP availability, and retreat without attack.
- No illegal attacks, resource overspending, or premature end-turn.
- One working slot; successful save before end-turn; no defeated state checkpointed.
- Confirmed defeat reloads the same checkpoint; three retries maximum; successful enemy phase resets the budget; distinct reaction combinations may override initial priorities.
- Map completion and unexpected prompts stop execution; scripted departures are not mistaken for defeat.
- Backup verification failures block trials; originals remain unchanged in portable testing.
- Injected buttons are released and pause status is explicit on handover.
- No runtime model usage, and no claims that API acknowledgment alone proves game behavior.

Use test-driven development, project-appropriate static checks and tests, and working-tree code review. Critical/Important findings block completion; fix them and rerun affected checks. The implementation plan and code remain uncommitted. A full autonomous battle must not be claimed complete while any integration gate is unverified.

## 12. Review notes

The explicit defaults for median weapon strength, normalized resource cost, common-enemy baselines, and deterministic retry profiles make the implementation reproducible. They are proposed operational definitions of the approved strategy and can be adjusted during this written-spec review.

The next step after user review is a separate implementation plan with exact files, meaningful failing tests, verification commands, and staged task scopes. This document does not authorize bypassing the remaining integration gates.
