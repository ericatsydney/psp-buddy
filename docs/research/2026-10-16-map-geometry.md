# Map dimensions and direct unit tiles — 16 October 2026

## Result and implemented use

The existing approved offline named-record inspector now decodes retained unit X/Y using
private evidence-bound profiles. No production code or structural unit-pool contract changed.
Three real CLI runs report all 107 candidate records accurately:

| Retained map | Dimensions | Candidate records | Direct coordinates |
| --- | --- | ---: | --- |
| Original slot1 | 28×28 | 69 | All within bounds |
| Portable slot1 | 34×26 | 12 | All within bounds; twelve pairs match existing visual cells |
| Development slot2 sample5 | 24×34 | 26 | All within bounds |

These reports still say `named_records_only`, with supplied offline provenance and every
live/tactical/autonomous capability false. Labels are snapshot-local slot labels, never
stable robot IDs. Unit identity, side, stats and action availability remain unknown in these
geometry-only reports. Source hashes are checked against the preceding actor-registry evidence.
Private config uses isolated empty roots for offline schema validation; it grants no live
trial readiness. Source emulator identities are asserted from retained context, not live auth.

## Defining layout and code

- u16 width at08E52A94; u16 height at08E52A96.
- Unit object u16+0x26 is tile X; u16+0x28 is tile Y.
- At088A2AAC, the game reads actor+0x0C to obtain the object, loads Y at+0x28 and X at+0x26,
  then tail-calls088A2ABC. That function indexes08E4EA94 +16*(Y*width+X).
- Separate lookup0897942C rejects negative coordinates and X>=width or Y>=height before
  row-major indexing. Another geometric endpoint check is inclusive; do not use that rule
  for cell indexing.
- Initializer088A9704 reads width/height from header words0/+4, derives payload header+32,
  passes the cell base and0x4000byte length to08820308, then stores dimensions. The helper
  contains a replacement word even in these saved states, so its original full semantics
  are not decoded here. The fixed span corresponds to1024sixteen-byte cells; all observed
  products fit it. Never follow untrusted dimensions into a larger window.

Four direct-coordinate code windows and five dimension/lookup windows match the two clean
states. A copy path08885E48 obtains two actor objects and copies their u16 tile fields;
its gameplay operation is not labelled. Other reads use signed halfwords. Future code must
reject negative/sentinel/out-of-range values; the existing unsigned field decoder already
rejects u16 sentinel65535 against the supplied small dimensions.

The previously investigated raw center pair at+0x18/+0x1C equals(16+32*X,16+32*Y) for all107
objects. Searching for a raw-center conversion was not needed to decode the direct fields.
That search remains a bounded negative result; do not claim it found an in-game conversion.

## Important negative results

Cell+0x0E is conditional state, not universal occupancy or validity: all784original cells
have0 while all884portable and816development cells have1. Cell+0x0C is a conditional lookup
output, not an established terrain class or unit index. Byte+9 has a separate getter but no
validated terrain meaning. Neither lookup licenses movement, targeting or action legality.
Map dimensions and positions alone do not establish a complete live tactical Snapshot.

## Reproduction and review

Private artifacts (ignored, no public game-byte fixtures):

- local/map-bounds-20261016/verify.py, findings.json, code.txt and findings.txt.
- local/unit-grid-conversion-20261016/verify_direct_tiles.py, direct-tile-findings.json and
  direct-tile-code.txt; the earlier negative searches remain alongside them.
- local/map-bounds-root-20261016/verify.py and findings.json: independent bounds/negative check.
- local/named-geometry-20261016/verify.py and findings.json: strict profiles/manifests, copied
  104byte source records and actual CLI reports in map-0/map-1/map-2.

Independent review found no material issues. One evidence-ID citation was corrected from
088A2AA4 to the demonstrated088A2AAC entry, then private CLI verification reran successfully.
No emulator, save/load, original-data writes, production changes or commits were involved.
The prior707-test/static/build checkpoint remains unchanged; a full suite rerun was unnecessary
for private profile research and documentation.

## Positioned report implementation — 16 October 2026

The subsequently approved positioned_representative_inspection descriptor now composes
selected robot/form/stat records with direct tile fields and captured map dimensions.
Existing named and structural descriptor outputs remain unchanged. ActualofflineCLI
checks match all107retained coordinates and allsix form-trial positionlists. Captured
Z Gundam(18,13) and G00(17,4) remain corroborated; this is not live tracking. The decoder
rejects missing/sentinel/out-of-bounds coordinates and dimensions above1024cells.
All tactical/autonomous/live capabilityflags remain false. Transform actions are excluded.
See specs/plans2026-10-16-positioned-inspection under docs/superpowers for exact contracts.
