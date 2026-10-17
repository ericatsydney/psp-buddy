# Offline menu-membership inspection design

Status: written design approved by the user on16October2026. Extends the completed
positioned reader within this explicit offline scope. No commits.

## Purpose and alternatives

Recommended: explicitly report code-backed Ally/Foe MENU membership, independently of
unknown tactical affiliation. Reuse selected robot/stat/tile records and the game's static
category masks. A raw group-to-side enum wrongly equates thirdparty with neutral; parsing
reusable UI list instances ties results to open menus and compaction/allocation state.
The proposed reader works from the existing captured object list without opening a menu.

Evidence: research/2026-10-16-affiliation-query-groups.md. DirectUI predicate reads object
byte+0x15; a fixed four-record producer supplies category0..3 to a four-mask table. Current
Ally/Foe screenshot samples independently select the matching20/5 filtered UI lists.
This binds supplied labels to observed menus in the supported evidence; it does not prove
hostility, player controllability, diplomacy or universal group semantics across games.

## Architecture and exact interfaces

Create src/psp_buddy/menu_membership_inspection.py (frozen MenuMembershipInspectionProfile,
MenuMembershipInspectionReport and pure decode_menu_membership_inspection) and
menu_membership_inspection_io.py (strict parse_menu_membership_inspection_profile).
Add explicit inspect-map descriptor kind menu_membership_inspection; existing kinds and
reports unchanged. Reuse positioned decoder, representative_spans IO and safe JSON helpers.
No live fetcher/controller, Transform action, battle model conversion or saves/reloads.

Exact JSON keys: kind=menu_membership_inspection,schema_version=1,positioned_profile
(complete existing positioned descriptor),menu_mask_table_address,expected_category_masks,
ally_category_index,foe_category_index,code_anchors,evidence_ids.
Masks are an immutable tuple of exactly four nonzero unsigned16bit masks, pairwise
nonoverlapping and together0xFFFF. Indices are distinct integers0..3. This is an explicit
user-supplied label mapping with bounded evidence references, not inferred from counts.
For real tested profiles indices0/1 and masks000F/F000/00F0/0F00 are corroborated; synthetic
public profiles may use different valid masks/indices. The actual captured table must
match expected masks exactly, not merely produce plausible counts.

Table address is4bytealigned in PSP userRAM with16bytes captured contiguously; each entry
is littleendianu32, notu16. Extra anchors1..16,each1..4096bytes,total<=16KiB; evidence1..32
unique bounded nonempty references. Exact key/type/bool/nonfinite/duplicate rejection uses
existing pure validators and bounded JSON parser. Identity is nested profile identity only.

Pure decoder signature(profile,spans,game_id,patch_id,emulator_version) returns immutable
report or ValueError; no I/O. Revalidate direct construction. Keep existing128spans,
64KiBper-span,1MiBtotal,RAM/contiguous/nonoverlap/identity safety through positioned decoder.
Construct private immutable nested profile copies combining its recipe fingerprints, new
query/producer anchors and an automatically calculated readonly-table fingerprint over
expected four u32 values. The legacy CodeAnchor type also represents this static data
fingerprint here: it is not claimed to be instruction bytes. Geometry composition then
adds its anchors. Deduplicated recipe/new/table/geometry union must fit existing32entry/
16KiB recipe budget; exact duplicates allowed, inconsistent/partial overlap rejected.
This reuse makes all new fingerprints including table avoid existing mutable semantic
regions and geometry dimensions. No olddecoder changes, caller mutation or limit widening.
Code anchors must cover the supported direct object-byte predicate and fixed category
producer in real private profiles; supplied fingerprints do not authenticate live identity.

## Decoding and output

1 Validate nested profiles, combined fingerprints and supplied spans via positioned reader.
2 Read fourtableu32entries, require exact expected masks and table restrictions above.
3 For every selected representative read rawu8(object+0x15) from captured object bytes.
   Supported version1 accepts0..15 only. Reject other raw values as unsupported, rather
   than silently applying MIPS low5bit wrapping or mapping unknowns to a side. The actual
   observed predicate is mask & (1 << (raw&31)); it is identical on this supported domain.
4 Require exactly one matching category for every representative. Match ally_index/foe_index
   to ally_menu/foe_menu; other categories yield outside_ally_foe_menus. Counts must sum to
   total representatives, including zero-unit cases. No robot-count constants.
5 Preserve base row order/stats/positions and add raw_menu_group_byte,menu_category_index,
   menu_membership. Top report adds category_counts (four ordered integers),ally_menu_count,
   foe_menu_count,outside_menu_count,category_masks,label_source=user_supplied_menu_label_mapping.
   Set inspection_kind=menu_membership_inspection and combine evidence refs without duplicates.
   Retain side in unavailable_fields, all other unknowns and every false live/tactical/
   autonomous capability. Explicit note: menu membership is not tactical allegiance.

Missing/invalid data, unsupported group, ambiguous coverage, identity/fingerprint/table
mismatch rejects entire report. CLI returns standard status2 error, no partialstdout or
fallback. No hardlinked/symlinked descriptor; existing manifest safeguards retained. Empty
reports require valid masks/dimensions/anchors, not guessed labels. No name decoding or
thirdparty/neutral label is assigned merely for being outside both menus.

## Acceptance and verification

Synthetic tests: variable/empty counts, ally/foe/other categories, raw0/15 bounds and16/31/32/
255 rejects, exact table/fingerprint mismatch, invalid/overlapping/noncovering masks, invalid
indices/bools/JSON, missing window, readonly-table fingerprint overlapping pool/stat/dimension
regions, partial/shared anchors,budget caps, unchanged caller profiles, preserved old outputs,
allfalseflags and no live imports/file writes. Meaningful failing tests before production code.
Private actualCLI: reproduce current20/5/1 across sixcaptures with WingZero outside both;
other retained map categorycounts24/25/20/0 and8/4/0/0 are raw category regressions, not newly
visually validated Ally/Foe labels. Use explicit composite static-code evidence when trial
capture lacks query/table bytes; no new emulator trial. Verify source identities/provenance.
Run fullpytest,Ruff,strictmypy,wheel/help and independent code review. Preserve staged and
unstaged work. No commits,pushes,battle activation or automatic PPSSPP closure/reconnect.

Written user approval is recorded; no live or tactical capability is authorized.
