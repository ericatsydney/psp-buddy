# Bounded offline unit-pool inspection design

Status: approved by the user on16October2026, following written-design review.
This extends the approved named-record inspector. It does not authorize live control or
replace the existing tactical acceptance gates. No commits or publishing are requested.

## Goal and alternatives

Turn the code-backed object table and actor catalogue into a reusable, tested offline
inspection path. It should find candidate slots and every associated robot/pilot record
without a full-memory signature scan or an invented choice of current pilot/form.

Recommended: bounded pool plus actor-owner/catalogue spans. It is supported by independent
instruction review and three map states, including a12-sprite visual check. A stack-only
reader has unknown lifetime and is rejected. Repeated full-RAM signature scans remain useful
for research but require much more data and do not establish durable ownership.

## Scope and exclusions

Add a new unit_pool_inspection descriptor kind to the existing offline inspect-map command.
The existing map_inspection descriptor and named-record report remain unchanged. The new
kind reports structural candidate slots and alias bindings only. It does not decode HP/EN/SP,
name text, absolute tile positions, side, action status, terrain or legal actions; existing
named-record inspection remains available for independently supplied stat records.

Do not ship the .ppst/Snappy research extractor, game assets, literal game-memory profiles,
a live memory fetcher, automatic emulator inputs or a tactical Snapshot conversion. Reject
unsupported layouts. Do not choose first/lowest pilot, infer primary crew, or turn a raw
stateword into an ally/enemy/neutral/third-party enum. A slot index is snapshot-local, never
a globally stable robot ID. Roster completeness and all live/autonomous capabilities remain
false/incomplete regardless of apparent counts or supplied evidence references.

## Architecture and interfaces

Create src/psp_buddy/unit_pool_inspection.py for immutable profiles, spans, records and pure
decoding. Create unit_pool_inspection_io.py for strict descriptor/manifest parsing and bounded
file reads, following map_inspection_io.py patterns. Extend cli.py dispatch for the new kind
under inspect-map; --records remains explicit with no live fallback. README/usage explain
that this is structural inspection, not a deployed battle roster.

An InspectionSpan contains an integer PSP RAM address and immutable bytes. The decoder takes
an immutable tuple of nonoverlapping spans, the immutable profile and explicit source identity.
It performs no I/O. At most32spans, each at most64KiB and at most1MiB combined are accepted;
all windows must fit08800000..0A000000. Boolean values do not pass integer validation.
Missing bytes, cross-gap reads and overlapping or duplicate windows reject the report.
A required subwindow may lie within one larger span; it must be wholly covered by one span.
No implicit concatenation across separate spans occurs.

The profile binds game/patch/emulator strings and map label; pool address/capacity/stride;
actor-owner address; expected actor-node-array address, actor stride/capacity and actor vtable;
nonempty bounded evidence references; and1..8mandatory code anchors (address,size,SHA-256).
Only the supported104-byte pool and16-byte actor layouts are accepted. Pool capacity is
1..256, actor capacity1..1024. Real profiles must use corroborated capacities, not assumptions
from one stage's roster count. Owner+8/+16/+20 must match the declared node/stride/capacity;
owner+12 supplies the actor-data address, which must be aligned, RAM-bounded and captured.
Each code anchor is1..4096bytes, combined at most16KiB; each exact subwindow digest must match.
These matches bind supplied bytes to a supplied profile, not to authenticated live identity.

A single pure function decode_unit_pool_inspection(profile, spans, game_id, patch_id,
emulator_version) returns an immutable UnitPoolInspectionReport or raises ValueError.
Do not reuse tactical models. The profile's fixed layouts interpret pool byte0 as occupancy
reference count and word+0x14bit0 as an inspection inclusion condition; this remains a
candidate filter, never a tactical deployment assertion.

## Decoding and output

1. Validate identity, profile bounds/types, span coverage and mandatory code anchors.
2. Read the28-byte actor-owner header. Verify expected layout, capacity and node-array value;
   validate the actor-data window before following it. No pointer is followed before validating its value and required target window.
3. Visit exactly the declared pool slots; include those with nonzero byte0 and stateword bit0.
   Empty slots with that bit set and occupied slots without it are excluded, counted separately.
4. Visit exactly the declared actor rows. Nonmatching vtables are ignored. Matching rows with
   null object pointer are unused and ignored. A nonnull object pointer must be an exactly
   aligned slot inside the declared pool, including inactive slots, or decoding fails.
   Rows targeting excluded pool slots are ignored. Included rows require two nonnull aligned
   RAM descriptor pointers; those pointers are retained without dereferencing or claiming IDs.
5. Preserve each included actor row separately, identified by its address. Do not deduplicate
   descriptors or form/crew aliases. Per-slot alias count must equal occupancy byte0; missing
   or extra aliases reject the whole result as an inconsistent supplied observation.
6. Return slots in ascending pool index, aliases in ascending actor address. Each slot reports
   slot_index, object_address, raw_state_word, raw_pixel_pair and actor bindings (actor address,
   mech descriptor address, pilot descriptor address). raw_pixel_pair is diagnostic raw data,
   not x/y tile coordinates; no coordinate transform is performed. Multiple distinct mech or
   pilot pointers are explicitly listed as ambiguities, not resolved.

The JSON report uses inspection_kind=unit_pool_inspection, mode=offline_read_only,
roster_completeness=candidate_slots_only, provenance=user_supplied_spans_and_profile,
live_authenticated=false, autonomous_available=false, tactical_snapshot_available=false.
It reports candidate_count, slot_capacity, exclusion counts and slot bindings. Side, absolute
coordinates, stat resources, map dimensions and action legality are explicitly unavailable.
There is no faction-count inference or primary-pilot field. Do not print raw input/code bytes.

## File contracts

The strict descriptor has kind=unit_pool_inspection and schema_version=1 plus the exact profile
fields above. Unknown/missing keys, duplicate JSON keys, nonfinite numbers, malformed digests,
wrong field types and unsupported layout versions reject. The records file for this kind has
kind=inspection_spans, schema_version=1, spans=[{address,path},...]. Paths resolve relative to
that manifest. File reads are bounded before loading all data; truncated/missing windows reject.
Do not accept a map_records manifest for this kind or an inspection_spans manifest for the
existing map_inspection kind. No .ppst input or compressed-state auto-detection is introduced.

## Failure and state protection

Errors are explicit validation failures without partial tactical results, retries, reconnects
or emulator side effects. A structurally valid result still has supplied, unauthenticated
provenance. Supplied profiles cannot declare readiness or change any capability boolean.
Do not broaden existing run or debugger commands. Synthetic verification needs no emulator.
Any later live integration still requires the project's complete backup and identity gates.
Preserve staged/unrelated user work and leave all implementation/spec/plan changes uncommitted.

## Acceptance and tests

Pure synthetic fixtures must demonstrate variable counts, nonzero slot origins, empty and
inactive negatives, a third raw-state group preserved without faction meaning, multiple crew
and forms retained, exact alias-count checking, slot-local IDs and deterministic ordering.
Failure tests cover bad layout/capacity, wrong identity/code bytes, missing or overlapping
spans, pointer arithmetic overflow/out-of-RAM windows, wrong owner metadata, misaligned
actor/object/descriptor pointers, null descriptors on included records, unknown manifest kinds,
malformed JSON/digests and bounded file reads. A poisoned live opener must remain uncalled.
A zero-candidate pool with no included aliases returns a valid empty candidate report.

Observe meaningful failing core and CLI/parser tests before production code. Run focused tests,
then the actual project suite, Ruff, strict mypy, package build and CLI checks. Independently
review tracked and intended untracked files against this spec and fix blocking findings.
Private retained-data comparisons may supplement synthetic tests but must not enter public
fixtures. Observed26/69/12 candidate totals are research examples, never universal roster counts.

## Handover

After written approval, use the writing-plans skill for exact bounded tasks and verification
commands, then implement core and IO/CLI in disjoint subagent scopes with dependent review.
This proposal does not claim the full autonomous battle milestone is complete. Remaining
primary selection, dimensions, affiliation semantics, legality and protected live integration
stay in the overarching plan.

## Exact version-1 contracts

These definitions resolve the shorthand above. The descriptor is one flat JSON object
with exactly these mandatory keys: kind, schema_version, game_id, patch_id,
emulator_version, map_label, pool_address, pool_capacity, pool_stride,
actor_owner_address, actor_node_array_address, actor_stride, actor_capacity,
actor_vtable, evidence_ids, code_anchors. There are no optional keys.
schema_version=1 selects the only supported binary layout; a separate layout_version
key is unknown and rejected. Addresses are JSON integers, never hexadecimal strings;
all numeric fields require exact integers, excluding booleans. Identity strings and
map_label are nonblank strings of at most256characters, with no control characters.
Source identity must exactly match all three identity fields. evidence_ids contains
1..32 distinct nonblank strings, each at most256characters without control characters.
Each code_anchors element has exactly address, size, sha256 keys. SHA-256 is exactly
64ASCII hexadecimal characters, normalized to lowercase. Anchor windows may not overlap.
The manifest has exactly kind, schema_version, spans keys; each span entry has exactly
address and path. Paths are nonempty strings without NUL; existing bounded file-reading
patterns apply. No other metadata may silently expand either schema.

All binary integers are unsigned little-endian. Pool, owner, node-array, actor-data base and vtable
addresses and all nonnull descriptor/object/actor pointers require4-byte alignment.
Pool slot offsets: +0x00 u8 occupancy_references, +0x14 u32 raw_state_word,
+0x18 u32 raw_pixel_pair[0], +0x1C u32 raw_pixel_pair[1]. Actor row offsets:
+0x00 u32 vtable, +0x04 u32 mech descriptor, +0x08 u32 pilot descriptor,
+0x0C u32 object. Owner offsets: +0x08 u32 node-array pointer,
+0x0C u32 actor-data pointer, +0x10 u32 actor stride, +0x14 u32 actor capacity.
The node-array pointer is validated for RAM range/alignment and equality only;
its target bytes are not required and no linked-list traversal occurs. Pool, owner
and dynamic actor-data windows must be pairwise disjoint. Code anchors cannot overlap
those data windows. Bounds are checked using full windows before reads or arithmetic
results are used. A matching actor targeting an excluded slot still requires a valid
object pointer; its descriptor pointers are ignored, so they may be null.

The public immutable types are UnitPoolInspectionProfile, InspectionSpan,
UnitPoolInspectionReport, UnitPoolSlot and UnitPoolActorBinding. Report serialization
has these exact keys: inspection_kind, mode, game_id, patch_id, emulator_version,
map_label, provenance, roster_completeness, live_authenticated, autonomous_available,
autonomous_execution_enabled, tactical_snapshot_available, candidate_count,
slot_capacity, exclusions, slots, unavailable_fields. All four capability booleans are
false. Identity and label values echo the validated profile. candidate_count and
slot_capacity are integers; slots is an ordered JSON array.

exclusions has exactly empty_slots, inactive_slots, empty_slots_with_active_bit integer
counts. empty_slots counts every slot with zero occupancy. inactive_slots counts
nonempty slots without bit0. empty_slots_with_active_bit is a diagnostic subset of
empty_slots. candidate_count + empty_slots + inactive_slots equals slot_capacity.

Each slot has exactly slot_index, object_address, occupancy_references, raw_state_word,
raw_pixel_pair, actor_bindings, ambiguities keys. Addresses and raw values serialize as
integers. raw_pixel_pair is a two-integer array. Each actor binding has exactly
actor_address, mech_descriptor_address, pilot_descriptor_address integer keys.
ambiguities has exactly mech_descriptor_addresses and pilot_descriptor_addresses keys.
Each value is the sorted distinct pointer array when there is more than one distinct
pointer of that kind, otherwise an empty array. Every actor row is retained independently
even when pointers repeat. No ambiguity array chooses a current form or primary pilot.

unavailable_fields is an object with exactly unit_id, hp, max_hp, en, max_en, sp, max_sp,
x, y, side, action_available, dimensions, phase, terrain, legal_actions keys. Every value
is the constant string not_decoded_by_structural_inspector. No CLI configuration values
can replace these fixed capability/provenance fields. CLI may wrap the report with the
existing configuration-validation metadata, documented separately from this exact report.

Code-anchor agreement does not prove coherent capture timing, capacity semantics or
live roster completeness. Alias-count agreement is a structural consistency check only.
Acceptance tests must cover all three noncandidate occupancy/bit combinations, the
exclusion accounting identity, excluded-slot null descriptors, precise report keys,
node-array equality without target capture, and every strict-schema limit above.


