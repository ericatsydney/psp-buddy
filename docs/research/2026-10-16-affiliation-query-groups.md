# Affiliation query groups: bounded offline investigation

## Confirmed correlations

The selected representative object links expose the same four-bit group through two
locations: `(u32(object+0x14)>>8)&0x0F` and `(u8(mech_header+0x3C)>>2)&0x0F`.
The header extraction was previously decoded from query code0884C504/508. The object-side
formula here is an observed correspondence, not yet an independently traced writer proof.

A private verifier joined the existing production representative reports back to their
retained captured spans. All237rows across two additional retained maps and six26-object
form observations agree between the two fields. All six current observations have exactly
the same object-to-group mapping, despite selected Z Gundam form/actor changes.

| Captured map | Group0 | Group4 | Group12 |
| --- | ---: | ---: | ---: |
| Original retained map | 24 | 20 | 25 |
| Portable retained map | 8 | 0 | 4 |
| Current slot2, each of six observations | 20 | 1 | 5 |

The current group0 count20 matches the user-confirmed Ally menu; group12 count5 matches
Foes. Their independent HP/EN identities match both Taurus2603/49 and4104/50, Vayeate13393/115,
Mercurius10507/140 and Euclid5211/89. Group4 is WingZero(mech147,HP1225,EN3), which the user
identified as a third party excluded from both menus. Z Gundam is group0 before/after/return.
Do not call the old object byte+1 grouping a side enum: it merges WingZero with listed foes.

## Limits and next evidence

These counts and individual identities corroborate this stage's menu membership. They do
not establish that every future group0/4/12 value means ally/third-party/foe or how other
numeric groups should be handled. Group4 has20objects in the original retained map, whose
menu membership was not independently confirmed here. No new screenshots are requested.

Existing static research says query0884C44C clears/marks headers according to a caller mask,
using the extracted four-bit group;0xFFFF bypasses filtering. The current next task is
tracing the actual Ally/Foe menu callers and their masks, including whether masks are
constant, contextual or derived from player/viewpoint state. A menu-generated header mark
is still not a durable side/current-form flag. No raw field is promoted to production side.

Private reproduction: local/affiliation-research-20261016.py and
local/affiliation-research-20261016/group-correlations.json. Reports reuse bounded captured
spans and selected representatives; no full live scan, emulator operation, source edits,
new saves, reloads, closure or commits. Existing positioned-reader checks remain930passed,
1Windowsprivilege skip; this investigation adds no implementation tests or capability flags.

## Actual menu filter traced (supersedes header-only inference)

The UI list path is0888BC3C ->0884C3A4(a2=1) ->089224F4 ->08922738 ->0894C968 ->0894C5DC.
It obtains object=u32(actor+12) and evaluates:

`object != 0 && (mask & (1 << (u8(object+0x15) & 31))) != 0`

The low5bit shift behavior is MIPS sllv semantics, not a universal0..15group assertion.
The menu initializer0888BB78 takes categoryindex fromu32(u32(a1)+8) and indexes static
masktable08B4DAE8. Category0/1/2/3 masks are000F/F000/00F0/0F00. Counting helper08886510
uses the same object byte and four masks. Nine exact relevant code windows match both
clean retained RAM sources; hashes and bounded disassembly are private under
local/affiliation-query-20261016 (analyze.py,code.txt,findings.json).

Applying that exact predicate to existing representative objects gives categorycounts:
original[24,25,20,0],portable[8,4,0,0],currenteachofsix[20,5,1,0]. Thus category0matches
this stage's20Allymenu units,category1matches its5Foes,category2containsWingZero alone.
This is menu/screenshot-correlated labeling, not a static proof of visible label-index
construction. The label-to-categoryindex producer remains unbound. The headergroup
formula remains a237rowcorroboration; the directUI predicate does NOT read the header.
Do not substitute the fourbit header formula for rawbyte+15 for unsupported future values.

No universal affiliation/hostility enum is implemented. In particular, thirdparty does
not imply neutral or safe from attack. A future reader should separate code-backed raw
menu-category membership from profile/evidence-supported labels and leave unsupported
relationships unknown. Next bounded research: trace the actual category parameter producer
and its visible label association; then write/review a concrete offline inspection design.
No new screenshots are required to repeat current known roster/HP/EN correlations.

Independent read-only claim review found no material corrections: direct predicate and
shift/table semantics agree with retained disassembly, categorycounts and237rowcorrelation
verified. Label-index construction/context remains the handover gap. Lastallowancecheck
89%used(11%remaining); boundedresearchtask complete, no new productionfeature started.

## Fixed category producer and active menu instances — 16 October 2026 continuation

The next producer link is resolved. The list-opening loop at088775F4..08877660 enumerates
four categories, calls the same count helper, and skips categories whose count is zero.
For each nonempty category it passes a fixed20-byte record from08B4BE40+20*category:
`[0x16A,-1,category,0,0]`. At08877634 it calls manager0889DDAC with UI type6 and a pointer
to that record pointer. The manager invokes the selected instance's initializer through
vtable+8; initializer0888BB78 reads that record's+8 category and uses the mask table.
Seven exact producer/manager/dispatch/init code windows and all four parameter records
match both clean retained sources. The category number comes from this fixed loop/record,
not from a unit count or a presumed robot-array position.

Important distinction: type6 uses a four-instance pool at08E4C1CC, stride0xB0. Instance
allocation and the parent's child-pointer list can compact away empty categories. Thus
UI pool index must NOT be interpreted as a category ID in arbitrary states. The dispatcher
uses UI type6 to choose this pool; it does not itself supply a category. Private proof:
local/affiliation-label-producer-20261016/verify_producer.py and producer-findings.json.

Independent retained-state analysis found three filtered UI lists in sample4(Foes) and
sample5(Ally): instance08E4C1CC has20group0 actors,08E4C27C has5group12,08E4C32C has1group4.
Their list contents are unchanged between samples. In the Foes screenshot sample only
second instance has u32+8 value01000000; the other populated instances have01000003. In
the Ally screenshot sample the first instance has01000000, and the second changes to
01000003. The base UI update code at0888B790..79C checks lowtwo bits and skips state3.
This is independent active-instance/menu-label corroboration, not a universal state enum.
Private reproducer: local/affiliation-label-review-20261016/review.py and summary.md.

Combined evidence now supports the following precise claim: fixed category0/mask000F
matches the observed Ally UI list; fixedcategory1/maskF000 matches the observed Foes list;
category2/mask00F0 contains the user's third-party WingZero in this stage. The parameter
producer is code-backed across the clean captures. Literal label-resource/text decoding,
other groups/categories, diplomacy and temporary control remain unverified. Do not call
thirdparty neutral/nonhostile, convert this into tactical allegiance, or identify UI pool
indexes with categories. No new screenshot/emulator request was needed for this result.

Next dependent work can prepare a concrete offline menu-membership reader design, with
explicit evidence-backed label mapping and unknown nonmember hostility, for user review.
Do not keep repeating counts/form/positions or chasing a literal plaintext label as if
that were required to preserve these observed-menu correlations. No production change.


## Approved offline implementation complete

The user approved menu-membership-inspection-design.md. Explicit newdescriptor
menu_membership_inspection now composes selected forms/stats/tiles with strict captured
mask-table matching and rawobjectbyte filtering. Sixretained currentcaptures report
20Allymenu/5Foemenu/1outside; WingZero stays outside, without neutral/hostility inference.
Othermapcounts remain raw regressions, not new visiblelabel proof. Profilelabelmapping
is explicit and all tactical/live/autonomous flags stayfalse. Fullsuite1010pass1skip,
static/type/build checks and independent review passed. Existing appsession untouched.
