# Positioned representative inspection design

Status: written design approved by the user on16October2026. The user requested adding
validated robot locations to the existing offline list. No emulator operations or commits.

## Goal and alternatives

Recommended: a new explicit positioned_representative_inspection descriptor wrapping the
approved representative descriptor. Reuse its selected object/actor/stat result, then read
direct object tile fields and bounded map dimensions from the same supplied spans. This
avoids changing existing profile/report contracts. Modifying representative version1 in
place is smaller but breaks its exact unavailable-fields/output contract. Using screenshots
or pixel-center arithmetic adds uncertainty and is unnecessary given direct-field evidence.

## Interfaces and scope

Add positioned_inspection.py (immutable PositionedInspectionProfile, GeometryProfile,
PositionedInspectionReport, pure decode_positioned_inspection) and positioned_inspection_io.py
(strict parse_positioned_inspection_profile). Reuse representative_spans manifest loader,
existing RepresentativeInspectionProfile/parser/decoder, InspectionSpan and CodeAnchor.
Add new inspect-map dispatch only; all existing descriptor kinds/output stay unchanged.
No live transport, input, Transform action, map movement, saving, loading or session closure.

Exact JSON descriptor keys: kind=positioned_representative_inspection, schema_version=1,
representative_profile (complete unchanged representative_inspection descriptor), geometry.
geometry has exact keys width_address,height_address,code_anchors,evidence_ids. Addresses
are even PSP user-RAM addresses; anchors1..16, each1..4096bytes, total<=16KiB, disjoint;
evidence1..32 unique bounded references. No embedded game addresses/assets shipped.
The new immutable wrapper's source identity comes solely from nested representative profile.

Decoder signature is (profile,spans,game_id,patch_id,emulator_version), returning an immutable
positioned report or ValueError. Revalidate pure API constructors, not just JSON. Require
existing128span/64KiB-per-span/1MiB-total, RAM bounds, immutable/nonoverlap/contiguous-window
and identity checks through the existing decoder; no implicit missing-window fetch. Require
all geometry fingerprints to match exactly before decoding geometry. Duplicate identical
anchors shared with the nested profile are allowed; partially overlapping/different anchors
are rejected. Deduplicated union of nested recipe anchors and geometry anchors must
contain at most32entries and at most16KiB. Decode through a private immutable copy of
the nested RepresentativeInspectionProfile with that combined code_anchors tuple, so
the existing decoder enforces new geometry fingerprints against all mutable semantic
regions (pool/catalogue/descriptors/tables/interpretedstats). Do not edit the caller profile
or widen harmless packed capture tails. Geometry data windows must not overlap any anchor.

Width/height are captured little-endian u16; require1..1024 each and product<=1024 (the
corroborated cell-storage bound), without reading/indexing the tile array. Width/height
storage addresses must differ and their2-byte windows must not overlap. For every selected
object, direct u16+0x26 is tileX and u16+0x28 is tileY; require0<=X<width and0<=Y<height.
Reject65535 and all out-of-range values, never clamp or derive from pixel fields. Require
positions for every representative. Empty reports still require valid map dimensions.

Result serialization retains the base report metadata/stats/counts/provenance and false
capability flags, combines base and geometry evidence references without duplicates,
changes inspection_kind to positioned_representative_inspection, adds
coordinate_system=zero_based_tiles and dimensions={width,height}. Each representatives row
adds tile_x,tile_y by exact object_address join; no new IDs or ordering. Remove only x,y,
dimensions from unavailable_fields; names,MV,side,actions,terrain/legality remain unavailable.
Do not claim live-current positions: supplied spans may be old or untrusted. No tactical
Snapshot, occupancy/terrain semantics, live roster completeness or legality promotion.

Malformed profile/file/identity/anchor/coverage/dimension/coordinate failures reject the
entire result; CLI returns standard status2 JSON error, with no partial report or fallback.
Regular-file/no-link descriptor safety matches representative kind; records loader unchanged.
Strict unknown/missing/duplicate keys, booleans, nonfinite and bounds rules remain enforced.
No original or portable saves/configuration are read or changed for this offline operation.

## Evidence, acceptance and review

Source docs/research/2026-10-16-map-geometry.md establishes dimensions28x28,34x26,24x34 and
107bounded candidate positions;12visible cells and G00/WingZero adjacency corroborate fields.
Latest retained26robot join places Z Gundam(18,13),Gundam00(17,4), using zero-based indices.
Private fingerprints must include the direct-tile and dimension/bounds getter code evidence.
Synthetic public tests must cover0/one/many representatives, zero/oversized/product-invalid
dimensions, largest legal and exact upper-bound/sentinel coordinates, missing coverage,
identity/anchor mismatch, bools/overlap, same-object selected-form change with same tile,
deterministic JSON, all falseflags and no transport/file writes. Existing CLI kinds regressions.
Private actualCLI checks must reproduce all107coordinates across retained maps and allsix
current trial observations from retained bytes only. Reuse prior private captured geometry;
no PPSSPP reconnection/new reads/trial needed. Run fullpytest,Ruff,strictmypy,wheel and
independentreview; document skips/unknowns and preserve existing uncommitted/staged work.

Written-design approval is recorded; implementation remains confined to this offline scope.
