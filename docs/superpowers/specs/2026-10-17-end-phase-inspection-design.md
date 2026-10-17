# Offline End Phase counter inspection design

Status: written design approved by the user in chat. No commits.

## Purpose and alternatives

Add the verified counter and End Phase count to the existing offline map report.
Recommended: compose the menu-membership reader so selected stats, locations and menu
labels remain available. A standalone raw-counter dump loses the validated roster and
UI count scope. Live action-availability integration is premature because causal action
consumption, phase ownership and command legality remain unverified.

Evidence: docs/research/2026-10-17-end-phase-count.md. No new screenshots are needed.

## Scope and interfaces

Create src/psp_buddy/end_phase_inspection.py with frozen EndPhaseInspectionProfile,
EndPhaseInspectionReport and pure decode_end_phase_inspection(profile, spans, game_id,
patch_id, emulator_version). Create end_phase_inspection_io.py with strict parser
parse_end_phase_inspection_profile. Add explicit inspect-map descriptor kind
end_phase_inspection, preserving every existing descriptor and its output.

Descriptor exact keys: kind, schema_version, menu_membership_profile, code_anchors,
evidence_ids. kind=end_phase_inspection; schema_version=1. Nested profile is the complete
existing menu-membership descriptor. Additional anchors: immutable tuple, 1..16 entries,
existing CodeAnchor validation; total combined inherited/new/table/geometry anchors must
remain within 32 entries and 16 KiB. Evidence references: 1..32 unique bounded nonempty
strings. Reuse existing strict JSON parsing, span limits and safe manifest/file access.
Identity is inherited exclusively from the nested profile. Reject invalid direct dataclass
construction as well as malformed descriptors; bool is not an integer.

No new configurable counter offsets or mask values: this version implements exactly
object byte+8 bits3..4 and End Phase query mask1. Supporting another recipe needs a new
reviewed version. Real private profiles must fingerprint the aggregate, object resolver,
zero helper and UI formatter/text evidence. Fingerprints are supplied evidence checks,
not authentication of a live emulator. No built-in private addresses or game bytes.

## Resolver boundary and decoding

1. Validate the complete nested menu report and combined anchors without mutating inputs.
   Reuse its validated representative source/cache agreement and captured exclusion table.
2. For every representative, apply the same initial enabled relationship-record pair
   search used by the game resolver. Use the representative reader's validated signed
   mech/pilot IDs and existing exclusion-record bounds/decoding; inspect that code before
   implementation and share a pure helper only if needed to avoid divergent predicates.
   If any matching enabled relationship record exists, reject the entire report as
   unsupported related-actor resolution. Do not guess the alternative actor.
3. Require a validated nonnull pool object for every row. The game's inverse zero-helper
   also counts null resolutions; this reader rejects those cases rather than calling
   them positive counters. Existing pool/representative gates remain mandatory.
4. Decode counter=(u8(object+8)>>3)&3, including values2 and3. Use supported raw menu group
   0..15 inherited from the menu reader. A row is in End Phase count scope iff raw group0
   (equivalent to the game's mask1 predicate on this supported domain).
5. Preserve all nested rows and add counter_value (0..3), end_phase_count_scope (bool),
   and counted_as_unmoved (scope and counter>0). Do not add action_available or can_move.
6. Add top-level inspection_kind=end_phase_inspection, end_phase_scope_count,
   unmoved_unit_count (count of qualifying actors, not sum of counters),
   displayed_unmoved_unit_count=unmoved_unit_count%100, and counter_semantics_note explaining
   the End Phase UI link and unknown Move/Attack legality. Combine evidence references.

Ally-menu membership uses a different mask and must not determine End Phase scope.
Counter2 contributes one actor. Empty maps yield zero counts after all profile/geometry/
fingerprint gates pass. Missing bytes, unsupported resolver cases, malformed tables,
identity mismatch or fingerprint mismatch reject atomically with ValueError. CLI uses
standard status2 with no partial stdout, live fallback or file mutations.

## Safety and exclusions

Preserve all unavailable fields and false live/tactical/autonomous capabilities. No battle
model conversion, phase enum, terrain interpretation, controller, MCP connection, emulator
launch, Move/Attack/End Phase/Transform input, save/load or checkpoint backend is added.
No trial is needed for this implementation. Any future trial follows fresh complete
SHA-256 save/config backups and its separate applicable approvals. Never commit or publish.

## Acceptance and verification

Meaningful RED-to-GREEN tests precede production code. Synthetic cases cover counters0/1/2/3,
scoped and unscoped rows, different Ally-menu versus mask1 counts, empty maps, 100+ actor
modulo display, relationship record enabled/nonmatching/matching cases, null rejection,
missing bytes, bad identities/fingerprints, overlap and anchor budget caps, immutable input
profiles, exact JSON keys/types, manifest safety and unchanged old CLI kinds.

Private retained reports must reproduce original scope24/unmoved13, portable8/5 and
current20/20, preserving every prior stat/tile/menu field. Use explicit composite static
code provenance for captures missing code, never call those live atomic observations.
Run full pytest, Ruff, strict mypy, wheel build/help and diff checks; independently review
all changes and intended untracked files. Do not rerun emulator trials to validate offline
logic. A causal action-transition trial remains a later dependency.

## Review

Self-review: bounded offline scope, resolver fallback only with explicit evidence, distinct
menu/count masks, counter2 and display modulo covered, no legal-action promise. Detailed
TDD implementation plan follows written approval, as required by the brainstorming workflow.
