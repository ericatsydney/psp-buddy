# Offline representative and form-stat inspection

Status: approved by the user on16October2026 for this offline reader. Existing approvals
also cover the completed structural reader and completed human-assisted form trial. No commits, publishing or emulator operations here.

## Purpose and alternatives

Report one evidence-bound current representative per candidate robot from supplied memory
spans, including its form/pilot IDs and corroborated record statistics. Preserve aliases
in the existing structural reader. A returned report describes supplied bytes; it does
not authenticate a live deployed roster or grant tactical capabilities.

Recommended: reconstruct the source-selection recipe and require exact set agreement with
the cached list plus one-to-one candidate coverage. It has 13 retained comparisons and a
six-observation Z Gundam/Waverider/return lifecycle supporting it. Cache-only decoding has
less implementation work but can accept stale representatives. Pool-only alias ranking
cannot establish the selected form/pilot and is rejected. See the research documents
2026-10-16-unit-table.md and 2026-10-16-representative-transition-validation.md.

## Scope

Add descriptor kind `representative_inspection` to offline `inspect-map --records`.
The new path reports object-local slot/address, selected actor and descriptor addresses,
mech/pilot IDs, HP/maxHP, EN/maxEN, SP, DEF, MOB and HIT. Both original inspection kinds
retain their current interfaces and output. This extension requires a new descriptor;
it never silently resolves the old structural reader's ambiguities.

Exclude decoded name strings, MV, effective boosted pilot combat statistics, coordinates,
dimensions, sides, actions, terrain, weapons, legality, capture/control, live fetches,
tactical Snapshot construction and planning integration. MV +0x05 has only pair-specific
corroboration and stays unavailable. Human screenshots can label private evidence, but
their names are not production lookup tables. Object/slot identifiers are observation-local.

## Architecture and pure interfaces

Create `src/psp_buddy/representative_inspection.py` for immutable profile/result types and
`decode_representative_inspection(profile, spans, game_id, patch_id, emulator_version)`.
It returns `RepresentativeInspectionReport` or raises `ValueError`; it performs no I/O.
Create `representative_inspection_io.py` for strict JSON profiles and bounded file loading.
Extend only CLI dispatch/help and user documentation. Reuse immutable `InspectionSpan`,
`CodeAnchor`, the existing pool profile/parser/decoder and bounded JSON/file helpers.
Do not import private trial code or research helpers into production.

The new decoder validates 1..128 nonoverlapping immutable spans, each 1..65536 bytes,
at most 1 MiB total within PSP user RAM. Required reads must fit wholly inside one span;
no implicit cross-gap concatenation, fallback or scanning. Validate addresses/alignment
and exact coverage before dereferencing. Reject booleans as integers. Existing structural
API retains its 32-span limit: derive a subset covering pool, owner, dynamic actor array
and its at-most-eight anchors, then call its decoder. Every required window is covered
by one original span, so this subset has at most eleven spans. Validate all128spans first.

## Exact descriptor and records contracts

The descriptor has exact top-level keys:

- `kind` = `representative_inspection`, `schema_version` = 1.
- `pool_profile`: complete existing `unit_pool_inspection` descriptor, retaining its
  identity/map label/evidence/layout/anchor validation; its identity is this report's identity.
- `source_root_global`, `cache_owner_global`, `blocked_mech_ids_address`,
  `selector_owner_global`, `pair_exclusion_owner_global`: aligned RAM addresses.
- `node_regions`: one or two objects with exact keys `address`, `capacity`, `stride`;
  stride is 12, each capacity 1..1664, aggregate at most2688, regions disjoint.
- `mech_descriptors` and `pilot_descriptors`: exact `{address, capacity, stride}`;
  capacities 1..2048; strides fixed at12 and8 respectively. Regions are disjoint.
- `code_anchors`: 1..32 additional CodeAnchor objects, at most16KiB total, each at
  most4096bytes, disjoint from each other. They authenticate supplied recipe code windows.
- `evidence_ids`: 1..32 unique bounded nonempty references.

Recipe version1 fixes selector capacity90, blocked ID count154 and pair-exclusion count127.
These are layout capacities, never robot counts. Do not expose arbitrary executable
expressions or pointer programs in JSON. Profile ranges and all followed data/code windows
must be RAM-bounded; mutable data windows must not overlap code anchors. Semantic storage
regions (pool, owner, catalogue, node regions, descriptor regions, fixed tables, and discovered
metadata/interpreted stat fields) must not partially overlap or overlap a different region category.
Identical targets within the same metadata/stat category may be shared by multiple actors;
this permits shared pilot records. Ordinary contained reads of the same region, including
pointer reads within a previously captured header, are not conflicting semantic regions.
Root pointer cells and list headers are views into validated allocations: permit their
contained reads, but reject root/list/node/table windows overlapping code or stat records.

Records kind is `representative_spans`, schema_version1, exact `spans=[{address,path},...]`.
Use the same regular-file safety, relative path resolution, exact-size and before-read
aggregate validation as existing spans IO, with the new128span limit. Do not change old
manifest limits or accept the new kind in old parsers. No duplicate JSON keys, unknown keys,
nonfinite numbers or malformed digests; no symlinks/hardlinks/special files. No raw bytes,
profile/game literals or game assets are printed or shipped. Supplied evidence is provenance,
not independently authenticated truth.

## Deterministic decoding recipe

1. Validate all types/identity/spans/anchors and reuse the structural candidate/alias join.
   Retain full actor catalogue rows for source-list membership, including noncandidate rows.
2. Define `u(a)` as an aligned captured little-endian u32, validated before reading.
   Source chain: `s=u(source_root_global); a=u(u(s+4)); b=u(u(a+4)); L=u(b+4)`.
   Cache list is `u(cache_owner_global)+4`. Each list has sentinel `L+20`, first node
   `u(L+12)`, actor `u(node)`, next `u(node+4)`. Every nonsentinel node must align to a
   declared node region, have all12bytes captured, and be unique in that traversal.
   Bound each traversal by1664nodes, independently of the2688-node storage capacity. Actors must be unique per list
   and belong to the validated catalogue; no arbitrary RAM actor or first-match fallback.
3. Validate descriptors for the union of source actors, cache actors and every candidate
   alias, not every unused catalogue row. Mech/pilot references come from actor+4/+8 and
   lie at exact declared strides.
   Descriptor+0 points to captured metadata whose first signed16 is the ID. Null descriptors
   mean ID-1 only for noncandidate actors; candidates require both valid descriptors/IDs.
   Reject IDs outside -1..2047, matching the private validated collector's bound; candidate
   aliases require nonnegative IDs. Descriptor+4 points to a captured mutable header. For stats,
   mech record=header+16, pilot record=header+8. For every nonnull relevant descriptor,
   require the complete header plus record (96mech/88pilot bytes), aligned/bounded/captured;
   resource-value semantics are checked only for accepted representative records in step8.
   Captured buffer coverage is distinct from interpreted semantic storage: adjacent mech
   records have80-byte stride, so96-byte header-plus-record capture windows can overlap
   unused bytes. Register only interpreted stat footprints (mech record+0..0x24 and
   pilot record+0..0x3E) for conflict checks, while still requiring full96/88byte capture
   coverage. Do not reject harmless capture-window overlap or permit actual field collisions.
4. Read154 signed32 blocked mech IDs and require sorted order. Selector data starts at
   `u(u(selector_owner_global)+4)` and holds90 signed32 mech/pilot pairs. IDs are -1 or
   0..2047. A mech ID-1 entry is unused, as in the observed recipe;
   do not reinterpret partially populated sentinels as a selected actor.
5. Phase1: source actors whose object byte+8 bit2 is set, mechID!=-1 and mechID not blocked.
   A nonnull object pointer must always be an exact pool slot. Phase2: for each nonunused
   selector pair find its unique exact source actor; include it only if the same object
   predicate holds. An absent pair is ignored by the observed recipe; ambiguous matches
   reject. Keep phase1/phase2 duplicates until applying the exclusions in step6.
6. Exclusion data=`u(u(pair_exclusion_owner_global)+4)`. Its127records start at data+4,
   stride20; each has mech signed32+4, enabled u32+8, pilot signed32+16. Remove matching
   pairs only where enabled is nonzero. Capture the entire required record window.
   Then reject any remaining duplicate actor, rather than silently deduplicating. This
   ordering matches the observed recipe; duplicates removed by exclusions do not fail.
7. Require reconstructed actor SET==cache actor SET; do not compare menu/list order.
   Every reconstructed/cache actor must map to exactly one structural candidate object,
   each object once, with no missing/extra objects. On any discrepancy reject the whole
   report. A clear dirty bit, selected Info globals or caller-supplied coherence flag
   cannot override this check. Info globals are not required and may be stale on the map.
8. For each accepted representative decode the 0x50-byte mech and pilot record windows.
   Mech u32+18 maxHP,+1C HP; u16+20 maxEN,+22 EN,+0A DEF,+08 MOB,+06 HIT. Pilot u16+3C SP.
   Require maxHP>0, HP<=maxHP and EN<=maxEN. Values are unsigned; SP maximum remains unknown.
   No effective combat-stat inference or repair of inconsistent values. Shared pilot/stat
   pointers are allowed when catalogue bindings support them; no aggregate SP sum.
9. Emit slots in ascending pool index. Slot/actor addresses and decoded IDs distinguish
   records; no stable campaign ID claim. Include source/cache/reconstructed counts, per-row
   alias count and supplied span address/size/SHA-256 provenance, never raw bytes.

## Output and failures

Immutable result rows serialize `slot_index`, `object_address`, `actor_address`,
`mech_descriptor_address`, `pilot_descriptor_address`, `mech_id`, `pilot_id`,
`mech_record_address`, `pilot_record_address`, `hp`, `max_hp`, `en`, `max_en`, `sp`,
`defense`, `mobility`, `accuracy`, `alias_count`. No untrusted label becomes a name.
Report `inspection_kind=representative_inspection`, `mode=offline_read_only`,
`selection_status=source_recipe_matches_cache`, `roster_completeness=candidate_slots_only`,
`provenance=user_supplied_spans_and_profile`, source identity/map/evidence and counts;
the result rows are the `representatives` array.
Set `live_authenticated`, `autonomous_available`, `autonomous_execution_enabled`,
`tactical_snapshot_available` all false. An explicit unavailable_fields map includes
name, MV, coordinates/dimensions, affiliation, action/phase/legality/terrain and maxSP.

Missing coverage, cycles, invalid pointers/descriptors, identity/code mismatch, resource
inconsistency, ambiguous selectors or cache/coverage disagreement raise ValueError; CLI
returns2 with its standard sanitized error, no partial success or fallback. Empty candidates
are valid only with empty reconstructed/cache sets; source-only noncandidate actors may exist.
No source CLI behavior or false capability flag may regress. No emulator interaction or
save/config writes occur, even when config includes a debugger endpoint.

## Acceptance and verification

Synthetic tests cover distinct form/crew aliases, variable/empty candidate counts, source
phases and exclusions, ambiguous/missing pairs, list/pointer/capacity attacks, exact code
and identity binding, file/manifest bounds, resource validation and deterministic output.
Include one meaningful form round trip: same object/pilot, selected mech/actor/stats change
and return, other bindings unchanged. It is a pure fixture, not a replay of game inputs.
Test a stale cache rejection even with an otherwise plausible selected Info record.
Poison transport/launcher hooks in CLI tests to prove no live fallback.

Private offline checks must reproduce69/12/26 on the existing retained maps and all six
human trial observations, including exact selector deltas and stat6/8/6,1000/900/1000,
115/125/115. Required spans can be exported privately from retained RAM/captured windows;
overlapping capture windows must agree byte-for-byte before canonicalizing disjoint inputs.
Never weaken the decoder to accept a private exporter defect. No new emulator trial needed.
Run full pytest, Ruff, strict mypy, local wheel and independent code review. Document
unsupported data explicitly. Keep all changes uncommitted and preserve the open PPSSPP session.
