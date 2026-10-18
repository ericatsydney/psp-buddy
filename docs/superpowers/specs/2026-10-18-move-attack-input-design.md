# Agent Move/Attack input for rule investigation

Status: proposed, awaiting user approval. Builds on the working agent input bridge
(`info_navigation.py`, `ppsspp_press_button`, PowerShell built-in screenshots).

## Goal

Let the agent perform one bounded Move or Attack on Destiny in a protected trial, capture
screens and memory before/after each stage, and compare them, without human button presses.
Replaces the human-controlled Move-down/Standby diagnostic.

## Exclusions

End Turn, save/load, cheats, memory writes, Spirit/Supply/Transform/crew, system menu,
automatic emulator closure, and any unit other than the named fixture unit.

## Approaches

1. Recommended: a second purpose set on the same bridge and class (`ActionNavigation`),
   same screenshot grounding, sequence, freshness and terminal-failure rules.
2. Generic "press any button": rejected; loses allowlists and the no-End-Turn guarantee.
3. Keep human control for the irreversible confirms only: safest, but keeps the slow loop.

## Interface

New press purposes, each bound to a button, a required screen context and extra fields:

| purpose | button | context | extra |
| --- | --- | --- | --- |
| open_move | circle | unit_commands, `Move` highlighted | highlighted_entry |
| move_cursor | arrows | move_range | none |
| confirm_move | circle | move_range | destination_tile (must equal approved tile) |
| open_attack | circle | unit_commands, `Attack` highlighted | highlighted_entry |
| select_weapon | arrows / circle | weapon_list | weapon_name (approved) |
| select_target | arrows | target_select | none |
| confirm_attack | circle | attack_forecast | target_name (approved) |
| standby_after_move | circle | unit_commands, `Standby` highlighted | highlighted_entry |
| cancel | cross | any action context | none |

Each action trial is declared up front in a request file (unit, destination tile or
target and weapon, tap budget 24). Confirm purposes are refused unless every field matches
the declaration and the frame is newer than the last input. One irreversible confirm per
declaration; a second needs a new declaration and fresh baseline.

## Data flow

Before each confirm: agent screenshot plus one coherent memory sample (existing observer).
After each confirm: screenshot and two stable samples. The bridge returns the raw
observation (no fail-closed on interpretation) and saves a before/after pair for comparison.

## Failure behaviour

Transport error or out-of-allowlist request is terminal (as now). Interpretation
mismatches (memory vs screen) are reported, not fatal. Unknown screen: stop, cancel out
only with `cancel`, never guess a confirm.

## Safety and protection

Fresh verified backups and the protected Launcher before every trial (unchanged). Trials
run on the portable writable copy; nothing is copied back. Declarations and every input
logged to `agent-navigation-inputs.jsonl`.

## Acceptance

Agent opens Destiny's menu, moves one tile down, finishes with Standby, and captures
screen plus memory at each stage; a second trial does one Attack on an approved target.
All tests (TDD per purpose, wrong-field/stale-frame/budget refusals), Ruff, mypy, Node
checks and independent review pass before any live trial.

## Open question

Whether Standby is included in this spec, or only Move and Attack.
