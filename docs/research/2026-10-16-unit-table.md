# Code-defined unit object table

## Result and boundaries

Offline analysis found a code-defined table at `0x08E61F50`, with224 slots of104 bytes
and exclusive end `0x08E67A50`. This supersedes reliance on the transient menu stack as
the only enumeration root. It does not establish a production-ready roster decoder.
Independent read-only agent review agreed with the root's instruction decoding.
No emulator was launched, controlled, closed or reloaded during this investigation.

## Code evidence

- Lookup `0x089261D0..0x08926218` (end exclusive) sign-extends the input's low16 bits,
  rejects negative or >=224 indices, computes index*104 and adds the literal table base.
  Callers must validate integer inputs before applying this original signed16-bit behavior;
  larger external integers must not wrap into apparently valid indices.
- Getter at `0x08926218` returns the base, including its return delay-slot instruction.
- Initialization at `0x08926224` iterates from base to exclusive end in104-byte steps.
- Allocation at `0x08926264` scans the same range. Empty-slot test `0x0892630C` returns
  whether byte0 equals zero. A successful allocation sets byte0 to1.
- Routine `0x08926194` calls another routine with (record,0,104); clearing is plausible
  but the target was not fully analysed, so no broader semantics are asserted.
- Two callers of the getter pass the full23296-byte span to another routine with reversed
  source/destination arguments. This independently supports the whole-table size; those
  routines were only read, never invoked.

A naive nearby-LUI search also produced false candidates when a register was overwritten;
only the independently decoded accessor/loop evidence supports the table claim.

## Retained-data checks

`local/stable-unit-table-20261016/verify.py` verifies14 full-RAM captures from three
separately launched instances of the same saved stage. It checks identical accessor code,
RAM bounds,224*104 span, candidate counts and inactive/empty negatives. Raw inputs and
hashes remain private. Reproduce with `.venv/Scripts/python.exe local/stable-unit-table-20261016/verify.py`.

Candidate condition byte0 nonzero plus word+0x14 bit0 produces26 objects in every sample:
20 with stateword0x1,5 with0xC01,1 with0x401. In both menu captures it equals the complete
26-object stack enumeration as a set. The menu stack retains screenshot order while table
slots provide stable indices for this build; table order must not be called menu order.

State bit alone incorrectly includes empty slot61 (`0x08E63818`) at candidate tile20,28.
Byte0 is zero and the allocator's empty test confirms this is an essential negative.
Zero-HP ally object `0x08E633A0` has nonzero byte0 but stateword0, and is also excluded.
Third-party Wing Zero remains included in the26, separately from both menu factions.

## Next gates

Validate another stage and changed deployment without discarding an unsaved session.
Resolve active form/primary pilot through code-backed relationships, then review an offline
reader extension with malformed/empty/stale/third-party cases before production changes.
Coordinates, dimensions, action availability and general faction semantics retain their
existing evidence requirements. Never treat224 as a deployed-unit count or expose raw
stateword values as a universal faction enum.

Current Windows process inventory returned no running PPSSPP process. This is a current
observation, not permission to relaunch or discard anything. Prior handoff files describing
PID7868 as open are stale and must not be reused as live ownership authentication.
Existing staged research/plan edits remain preserved. No commits were created.


## Actor catalogue owner and bounded correlation

Code construction at0889C5F4..0889C63C passes owner08E4B318, node array08E43424,
object stride16 and capacity1024 to initializer08888768. A second owner08E4B360 uses
node array08E46434, capacity1664, with no actor-data span. Destructor wrappers independently
use node size12. The node-array starts are NOT established live list heads; earlier
next-pointer walks from their first entries must not be called supported iterators.

First owner+8 stores the first node-array address; +12 stores the actor-data base;
+16 is16 and +20 is1024 in allthree compared maps. The +24 counter is consistent with
unused capacity, but its full update lifecycle was not decoded, so the helper calls it
counter_at_owner_24 rather than asserting allocator semantics.

Scanning the bounded1024*16 actor-data span for the expected actor vtable and joining
object pointers to occupied/enabled pool slots recovers every active candidate:
69objects/91actor rows,12/12,26/56. Counts of rows per object equal pool byte0 throughout.
The last inactive zero-HP object's57th actor row in the development fixture is correctly
excluded. Resource/form aliases remain distinct; duplicates are not collapsed into arbitrary
primary pilots. Full-RAM signature scanning is no longer needed for this structural check.
Reproducer: `local/stable-unit-table-20261016/verify_actor_registry.py` and actor-registry.json.
Core pool+actor+owner spans total39708bytes, excluding code/identity checks, descriptor tables
and stat reads. This is a byte-count comparison, not a measured live performance result.

## Form and crew evidence; rejected shortcuts

Mech mutable-header byte+0E (inspection-record minus2) is1 for exactly one distinct form
in every multi-form group checked across the69-object and26-object states (4and6 groups).
In the current menu it selects Zeta122, Methuss134, Macross377, and other form indices526,
330,346. The prior other-map state selects Methuss133 instead. This is useful correlation,
but a defining code path is not yet established; no production form selector follows.

No credible universal primary-pilot selector was found. Header+0F and one static metadata
flag distinguish some crew groups but fail other groups. An explicit two-field hypothesis
failed held-out data: the69-object state's object08E63060 has three current-form pilot
rows419/420/421 all with header+0F1. Do not prefer the first or lowest-numbered pilot.
A preliminary reported static-byte offset was corrected from+10 to+12 during investigation;
no result relies on that mistaken offset or on incidental ability-ID bits.

Actor vtable08CDC094 supports destructor/constructor and descriptor methods, not a proven
primary predicate. Descriptor+8 references extra per-form record state; it is not a supported
current-form selector. Construction/equality helpers were traced but resolve no crew choice.

Live dumps contain PPSSPP replacement/emuhack words in some code ranges. The two decompressed
states provide matching original instructions there: e.g08923EC8 is8C820004 in both, versus
68022856 in live sample5. Do not disassemble0x68 replacement words as original game code.
The save path clears replacements/JIT patches around Memory serialization in
[PPSSPP SaveState.cpp](https://github.com/hrydgard/ppsspp/blob/v1.20.4/Core/SaveState.cpp).
Use clean state instructions only after matching relevant unmodified code and provenance.

## Approved implementation verification,16October2026

The user approved the written structural-inspector extension. Production decoder and strict
inspect-map IO/CLI now implement it; see src/psp_buddy/unit_pool_inspection.py and
unit_pool_inspection_io.py. Core TDD observed missing-module red before implementation,
then55 focused tests passed. IO/CLI added49 tests, alongside existing named-map regressions.
The full suite reports707passed; Ruff check . and strict mypy src(23files) pass; local wheel
build succeeds. Synthetic documentation JSON also passed a real subprocess CLI invocation
with1candidate and2aliases. Independent final review reports no Critical/Important/Minor
findings; reviewer tmp_path tests were sandbox-limited, while root full-suite execution
with Windows temporary-directory access passed. No emulator/save actions or commits.

Private production comparison local/unit-pool-production-20261016/compare.py verifies source
hashes against the earlier actor-registry evidence, supplies only40040bytes per map including
332code bytes, and reproduces69objects/91aliases,12/12 and26/56 exactly. Every actor row,
mech pointer and pilot pointer matches the prior independently assembled research join.
This establishes the bounded reader's agreement with those retained observations, not live
capture coherence, universal deployment semantics or tactical readiness. Report booleans stay
false and primary-form/crew ambiguity remains explicit.

## Current-form byte: defining query path and negative result

Offline code review found a writer/reader path at0884C44C..0884C5C0, matching both
clean states. It clears mech mutable-header byte+0x0E across a source actor list,
marks eligible headers from a separate cached list, then returns source actors whose
mark is nonzero. Clear0884C4B0=A040000E; set0884C524=A043000E. Selection reads
bits2..5 of header+0x3C and applies a supplied mask;FFFF bypasses filtering. This is a query
membership mark. It does not establish a persistent intrinsic current-form flag.

Root independently checked ten static candidate callers in both clean states. Two
pass mask1 in the delay slot (0885B170/0885B174=24050001 and
089A2FDC/089A2FE0=24050001); several passFFFF, and0884C3CC passes a dynamic
low16mask. These are static candidate callsites, not traced live execution. Reproducer:
local/query-mark-callers-20261016/verify.py and findings.json. Neither category-mask
semantics nor the cached-list selection predicate follows from these instructions.

Getter0884C6A8 follows089293A4 ->08929490 ->08926928 ->08922FE4 to the source
list (original09647050, portable091C01A0). Getter0884C6E4 follows08929488 ->
0894C494 to a separate cached list at u32(08ECF708)+4 (original091C4FF4,
portable091C5254). Bit0 of08B47D2F requests rebuilding via0894C338. Its retained
valueFA has that bit clear in both states. Why the cached list currently correlates
with active forms remains a separate question. Do not use the mark as a selector
or introduce it into the structural inspector. No emulator inputs were needed.

## Cached representatives: bounded corroboration

The cache itself is a promising representative source. Root independently reproduced
69/12/26 entries, one actor per candidate object, with exact object-set agreement against
the bounded pool/actor join. Traversal: list=u32(08ECF708)+4; first=u32(list+12);
actor=u32(node); next=u32(node+4); stop at sentinel=list+20. Enforce RAM bounds,
cycle detection and a1024-node research cap. Reproducer and complete rows:
local/cached-actor-list-20261016/verify.py and findings.json.

Agent analysis across13retained observations (the two clean states plus11samples) reports
no parse errors, no duplicate objects, exact candidate-object sets and13matching selected
Info actor links. Root checked those result invariants. Known selections include Gundam00,
WingZero, Taurus, Shenlong and Dancouga. Current26cached actor addresses also exactly match
the independently decoded26-entry menu stack. Repeated snapshots of the same character are
corroborations, not13distinct visible-character checks. No new screenshots are needed to
repeat these checks. Reproducer: local/current-form-code-20261016/analyze_cache.py,
cache-analysis.json and findings.md, retaining source hashes and seven clean code windows.

A decisive mark-byte counterexample appears in the Ally-menu sample: the cache still has
26representatives, but20headers have mark1 and6have mark0. The20ones match raw pool state1;
fivezeros matchC01 and onezero matches401. Original69 and portable12 caches have allmarks1.
Do not use mark+0E to drop other cached objects or to choose current forms.

The exact mask extraction is `(byte_at_header_3C >> 2) & 0x0F`: instructions0884C504
00031E80 (sll26) and0884C508 00031F02 (srl28). A preliminary low-six-bit description
was incorrect and corrected before any production use. Current raw bytes1/17/49 produce
query groups0/4/12, with counts20/1/5. This supports the screenshot-correlated query filter;
it does not establish universal faction labels or allegiance transitions.

Cache builder0894C338 calls intermediate source builder089230E0 and callback0894C408.
The callback rejects certain signed mech/pilot ID pairs using a127-record,stride20 table;
matching mech at+4,pilot at+0x10 and nonzero word+8 excludes the pair. Applying only this
predicate to all enabled aliases leaves76rather than69 representatives in the original
map and37rather than26 in the development map. It is not a standalone primary selector.
Source construction remains undecoded. Cache validity across mutations, loads, transforms
and stage transitions is unverified. Future work should trace089230E0 and cache invalidation,
then obtain protected lifecycle evidence before proposing a representative-reader extension.
The implemented structural reader intentionally remains unchanged and retains every alias.

## Representative source decoded, 16 October continuation

The source-builder recipe now reproduces the complete cached representative SET in all
13 retained observations: 69/12/26 actors across three maps, with no duplicate predicted
actors. Root independently checked all result invariants and nine byte-identical defining
code windows in the two clean states. Exact order matches 10/13 observations; current
samples3..5 differ in order only. Do not use the recipe to predict menu sorting.

Phase1 of089230E0 traverses source actors via callback08923210, requires object byte+8
bit2 and rejects signed mech IDs in the sorted154-entry signed32 array08ECF46C..08ECF6D4.
Phase2 visits90 explicit signed32(mechID,pilotID) pairs, stride8, at
u32(u32(08ECF6D8)+4), resolves exact pairs and applies the same object predicate. A separate
127-record, stride20 table then excludes matching pairs with nonzero exclusion flags.
Original map:74+4 source actors minus9 aliases gives69. Current map:29+6 minus9 gives26.
Portable map:12+0 minus0 gives12. The nine exclusions share objects with retained actors;
they remove extra crew aliases, not nine deployed objects. These are code-backed steps,
not a lowest-index/first-pilot heuristic. Gameplay meaning of object bit2 remains unlabelled.

Correction: the pair-exclusion records have mechID at+4 and pilotID at+0x10. Earlier notes
reversed these because08939458 computes pilotID first; register argument flow establishes
the correct mapping. Old private script/JSON and the preceding research paragraph were
corrected. Applying just this corrected exclusion to every enabled alias yields76/12/37,
not69/12/26, so the full source-builder remains necessary. Production code never used the
incorrect interpretation. Retained complete recipe and input hashes:
local/representative-source-20261016/analyze.py, findings.json and findings.md.

## Cache lifecycle limits

Static evidence confirms a rebuild/dirty-bit mechanism, owner creation and teardown.
Getter0884C6E4 tests08B47D2F bit0, clears it at0884C71C BEFORE calling rebuild0894C338
at0884C720. A clear bit therefore cannot prove a coherent capture or completed rebuild.
Invalidator0884C744..758 ORs0x0D into the flag; its tail jump is088E45D0. Owner getter
0894C494 allocates40bytes and installs08ECF708; teardown0894C450 clears that global.
Mutation-coupled invalidations exist, but no transform/deployment/stage/load labels were
established. The bounded first2MiB scan found24 direct invalidator callers and62 candidate
byte stores,47 with nearby bit-setting patterns. These are not62 proven global writes;
register-base data flow, indirect calls and code outside the window remain unanalysed.
Exact code words, both input hashes and bounds are retained in
local/cache-lifecycle-20261016/verify.py, findings.json and findings.md.

Next: validate cache/source-table refresh after actual form, crew and stage changes under
fresh verified save/configuration backups, or first trace those precise lifecycle paths
further offline. Compare source recipe, cached set and visible selection before/after;
require structural consistency and do not trust a clear dirty bit alone. Existing screens
need not be repeated. No production changes or emulator actions in this continuation;
707-test verification remains the preceding implementation result, not a newly rerun suite.

## Noon continuation: selector refresh, map bounds and direct tile coordinates

Further code-backed evidence now identifies a selector-table replacement path08948D7C,
which replaces an old actor's matching mech entry with a new actor's exact mech/pilot IDs.
Success paths through0885F938/99C/A00 converge on0885FC84..98 and set the representative
cache dirty byte. Separate actor-state handoff08975B28 invalidates and transfers descriptor
state bits; no complete UI transaction or coupling between these paths is asserted.
Evidence: local/selector-lifecycle-20261016 and local/cache-transition-paths-20261016.
Mech-header+3Cbit0 and pilot-header+58bit0 are not a representative shortcut: both bits
still select multiple aliases for9original objects and10development objects. Portable12
has no ambiguous aliases and is not a sufficient positive test. Reproducer:
local/handoff-bit-selector-20261016/verify.py and findings.json.

Map width/height and direct object tile X/Y are now defined in game code and compared across
all107retained objects; see2026-10-16-map-geometry.md. Existing approved named-record CLI
profiles report these coordinates without a production change. Gundam00 is(17,4), WingZero
is(18,4), agreeing with the user's earlier right-hand-adjacent confirmation. The portable
12direct pairs exactly match prior visible-cell corroboration. Neither result establishes
terrain, legality or an authenticated complete live roster.

A written protected reversible form-change trial has been prepared and independently
reviewed (one stable-vs-diagnostic timing ambiguity resolved; no remaining blocking findings).
Spec: docs/superpowers/specs/2026-10-16-representative-transition-trial-design.md. User approval
is pending because current approved inputs are cursor/info navigation only. No trial launched;
no existing PPSSPP process was present at the beginning of this continuation. Existing screenshots
need not be repeated. No production code or saves changed, and no commits were created.
