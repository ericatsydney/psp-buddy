# Move and Attack only MVP action scope

Status: written design approved by the user in chat. Repair means healing in this game.
Move and/or Attack only; Spirit, Repair, Supply and Transform excluded.

## Goal and alternatives

Make the existing planner/executor obey the reduced MVP scope before a live action trial.
Recommended: enforce in both planner and executor. Planner-only filtering leaves manually
supplied or stale support-action recipes executable. Documentation-only deferral leaves the
current planner requiring unknown healing capabilities and preferring Repair/Trust.

This is an offline behavior change. No live bridge or battle acceptance is enabled.

## Behavior

Player-unit gameplay commands are Move and Attack, including move then attack when fresh
observations establish legality. Exclude all Spirit commands (including Trust), Repair,
Supply, Transform and crew changes. Do not add support actions or discover their memory
fields for MVP. Existing turn progression (Wait/End Turn), enemy reactions, safe dialogue
handling and handover remain orchestration controls under their prior safety gates; this
scope does not authorize sending any of them to the emulator now.

Keep existing injury retreat behavior and HP safety thresholds. Injured allies may move to
a validated safer tile or wait/handover under existing rules; they no longer trigger a
healing search. Preserve target priorities, weapon/resource validation, boss rules, unknown
legality rejection, fresh snapshot requirements and reaction/recovery behavior.

## Architecture and interfaces

Change existing choose_action(snapshot, policy) behavior in src/psp_buddy/planner.py:
remove Repair/Trust selection and all dependence on repair_capable,trust_capable,
legal_repair_targets,legal_trust_targets,Trust SP/cost solely for healing. Unknown values
for these excluded features must not block a valid Move/Attack decision. Do not infer a
legal action from a positive End Phase counter. Supplied support actions are never selected.

In src/psp_buddy/executor.py reject Repair/Trust selections before any button command,
even if a matching legal-action entry and recipe are supplied. Preserve fail-closed
handover/release behavior; releasing held controls is allowed safety cleanup. Supply and
Spirit other than Trust have no existing ActionKind; do not add enum members for them.
Retain existing data fields/enums for parsing compatibility and historical fixtures; they
do not grant execution permission. No new default-on opt-in for excluded actions.

Update affected synthetic planner/executor/supervisor scenarios to assert the reduced
scope instead of expecting healing. Keep unrelated legacy coverage. Public method
signatures remain unchanged. No production reader, save backend, transport or launcher
changes. Existing run command remains disabled.

## Failure handling and acceptance

Observe meaningful failing tests before production edits. Required cases: injured allies
with unknown healing/SP data do not request healing evidence; supplied valid Repair and
Trust options are never chosen; eligible safer retreat still selected; normal legal
Move/Attack and resource checks preserved; direct executor Repair/Trust requests hand over
without sending a recipe; missing Move/Attack evidence still hands over. No false live
capability flags or side/phase assumptions. Verify repeated Move/Attack planning only from
fresh legal observations rather than assuming movement leaves attack available.

Run documented full offline pytest with a unique workspace-local basetemp, Ruff src/tests,
strict mypy, wheel/help and diff checks. Independently review working-tree changes and
intended untracked files, fix Critical/Important findings, preserve existing staged work.
No emulator action, save mutation, commit or publishing is part of acceptance.

## Next dependency

After this scope guard passes, design a bounded human-assisted Move/Attack observation
trial to establish action-counter consumption, moved state and post-move attack legality.
A live trial needs separate written review and fresh complete SHA-256 original/portable
save/config backups. Do not launch, load or operate a pre-existing user session now.

Self-review: exclusions are explicit, executor guard prevents bypass, historical models
remain readable, excluded unknown fields do not obstruct MVP. Turn/reaction controls are
retained as prior orchestration scope, not extra player-unit abilities.
