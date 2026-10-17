# Selected Unit screen memory links

## Scope and evidence

Game ULJS00460 version 1.01, English v0.8, PPSSPP 1.20.4. Research only;
no production binding or automatic battle behavior is enabled.
Protected trial: `20261015T065827988941Z-c31825d738e445cc9db4e7fa0ceb0173`.
Private screenshots, RAM dumps, hashes and comparisons remain in its `user-evidence` folder.
Samples: Shenlong, Gundam 00, unchanged Gundam 00, Shenlong, Dancouga Nova.

## Selected records

Little-endian u32 chain for mech: `u32(u32(0x08E60674) + 4) + 0x10`.
Pilot: `u32(u32(0x08E60678) + 4) + 8`.
Duplicate selected globals at `0x08E60680` and `0x08E60684` corroborate both.
The return to Shenlong reproduced the same record pointers and HP/EN/SP.
Dancouga Nova was a held-out third robot: all 14 checked visible values matched,
including HP5782, EN9, SP44 and level33.

| Screen | Mech record | Pilot record | Mech/pilot descriptor indices |
| --- | --- | --- | --- |
| Shenlong/Wufei | 0x08E92340 | 0x08EA6270 | 143 / 150 |
| Gundam 00/Setsuna | 0x08E93A60 | 0x08EAA040 | 217 / 242 |
| Dancouga Nova/Aoi | 0x08E95040 | 0x08EADC0C | 287 / 331 |

Candidate mech descriptor table base `0x08E67C80`, stride12; pilot base
`0x08E6A3F8`, stride8. These bases are inferred from three observed rows.
Pilot level is a byte at record+0x46, not a u16. Pilot SP is u16+0x3C;
will is u16+0x3E. Combat fields at +0x1E through +0x28 match all three screens.

## Relationship lists

Arrays `0x09601B20..0x09601F40` and `0x096027F0..0x09602C10` (end exclusive)
each contain132 unique signed32 mech/pilot pairs. They are permutations of the same
pairs and remained byte-identical across all five samples. Container headers at
`0x09601330` and `0x09602000` contain the respective base and count0x84.
Dancouga/Aoi pair287/331 occurs at first-list row59 and second-list row37.
These observations support stable relationship lists, not proven deployment lists.

A separate16-byte descriptor-pair row at `0x091C04D0` associates Dancouga287
with Aoi331. The next three rows share mech287 with pilots332..334, consistent
with a multi-pilot robot. Their fourth words are pointers, not unit coordinates.
Never assume one pilot row equals one deployed robot.

## Next validation gates

1. Fresh backed-up restart/reload; reauthenticate and corroborate selected chains.
2. Repeat on a different stage; distinguish stable build tables from stage allocations.
3. Identify deployed membership, side and world coordinates against visible map units,
   including inactive/reserve negatives. Cursor coordinates alone are insufficient.
4. Only then add evidence-bound production decoding with meaningful failing tests,
   focused implementation, complete verification and independent review.

Current findings do not establish deployment count, side, map position, action status,
terrain or legal actions. Reload and cross-stage checks remain outstanding.


## Combined selected relationship and checkpoint

Globals `0x08E6067C` and `0x08E60688` track the selected16-byte relationship row:
Shenlong `0x091C0660`, Gundam00 `0x091C0310`, Aoi `0x091C04D0`.
Both follow the same A-B-B-A-third sequence as the separate descriptors. This directly
links the selected screen to the relationship rows, without proving deployment membership.
Private bounded analysis: `local/third-unit-relation-20261015/findings.json` and
`dynamic.json`. Region0x096E24xx contains references worth investigating, but its mixed
record shapes and packed words have no validated coordinate interpretation.

Reload was not performed: PPSSPP's unsaved-progress exit dialog is awaiting explicit user
confirmation. Current process remains open; no save, load or battle command was issued.
Latest quota checkpoint:11% five-hour allowance remaining. A new launch must start with
fresh complete verified backups after closure; do not reuse the previous trial receipt.


## Position-object investigation and independent-launch comparison

Bounded offline analysis under `local/position-object-research-20261015/` found57
relationship rows referencing27 distinct104-byte objects. Nineteen objects form a
contiguous run `0x08E62F28..0x08E63678` at stride0x68. For these19, first word equals
the number of relationship aliases; Aoi has four aliases. Do not count pilots as units.
Object+0x18/+0x1C contain candidate pixel positions of form32*n+16:
Gundam00 (560,144), Shenlong (496,528), Aoi (528,528). Candidate tile conversions
are (17,4), (15,16), (16,16), pending visible map corroboration and coordinate origin.

Comparison with three retained dumps from independent trial
`20261015T012546647014Z-21454d99fc34438b84254e5277322275` showed all57 relationship
rows and the three named mech/pilot records identical across eight samples. All27
candidate positions stayed fixed as cursor coordinates changed17,4 ->18,4 ->17,4.
This distinguishes these objects from cursor motion, but does not establish deployment.
Twenty-six full objects differed across launches only at word+8 (extra0x20 in older
captures); therefore that flags word must not be treated as an immutable profile field.
The third named record joins and coordinate-like values are stable across these launches
of the same saved state. The selected-global chains still need fresh Info-screen reversal
checks; this offline comparison is not cross-stage validation.

Eight non-main objects have relationship descriptor indices inconsistent with packed
object+4/+6 values, and mech-record embedded indices are zero. Their semantics are
unresolved: do not label them enemies or deployed units using pointer presence alone.
Three unreferenced following object slots have first word zero and (16,16) pixel-like
values, further demonstrating that a plausible coordinate is insufficient membership evidence.

Evening continuation: the prior process exited and preservation verification passed.
After clarification, the user explicitly authorized a fresh fully backed-up slot-2 trial.
This overrides the earlier no-reload restriction for this one launch only; it does not
permit discarding a subsequent unsaved session. Fresh backup trial ID:
`20261015T120025749948Z-0289b926396c4c3683c13be0b1f44c51` (launch pending verification
at time of this note). The first sandbox process-inventory check failed closed; unrestricted
execution of the unchanged protected launcher retained all backup/non-writing checks.


Fresh launch checkpoint: trial20261015T120025749948Z-0289b926396c4c3683c13be0b1f44c51
passed complete backups and loaded expected slot2 HP5000/EN121/SP55. Owned PID7868;
manual handoff helper remains open. New full-RAM sample0 confirms all57 relationship
rows and27 position objects match the older cursor-reversal launch. Compared with the
later Info samples,26 objects differ only at flags word+8 by0x20; coordinates are stable.
Evidence: `local/position-object-research-20261015/restart.json` and trial `user-evidence`.
Initial-map selected globals point to relationship091C0D80, so no Info-selection validation
is inferred. Native Debug screenshot succeeded (`fresh-map.jpg`); the subsequent Circle
keyboard tap did not visibly open a command menu. Further game input stopped. User was
asked to manually open Gundam00 Unit tab and reply ready, with no new screenshot required.
Next sample request index is1. Keep this new session open and do not discard/reload.
Private continuation-checkpoint.json retains helper details. No live battles or saves issued.
Git baseline is now user commit a964b1f; only research/plan docs changed in this continuation.
Recurring automation covers the full approved MVP at300-minute intervals; future runs must
read current state and respect unmet evidence/design gates rather than duplicate generic code.


Fresh-launch Info validation completed after user manually opened Gundam00 Unit tab.
Sample1 resolves selected descriptors08E686AC/08E6AB88, relationship091C0310,
mech08E93A60/pilot08EAA040 and object08E63130. Both duplicate globals and relationship
fields agree; HP5000, EN121, SP55, level36 and will150 match established visible values.
CPU/UI resumed (false,false). Evidence: `gundam-info-restart-validation.json` in this trial.
This passes the named selection link across a fresh launch, not cross-stage deployment.
Next held-out target is the robot one tile right of Gundam00 (candidate tile18,4), whose
linked record differs from main allied records. User asked for its Unit screenshot and to
leave it open; next sample index2. No further Gundam00 screenshot required.


## Enemy-boss corroboration

User identifies tile immediately right of Gundam00 as enemy boss. Supplied Unit screenshot
shows Wing Gundam Zero/Quatre. Fresh sample2 selects mech descriptor08E67DDC (index29),
pilot08E6A590 (index51), relationship091C0B30 and object08E62158. Inspection records are
08E8FFA0/08EA1FEC. All duplicate selected globals agree. Eight checked basic values match:
HP1225, EN3, DEF1600, MOB120, HIT150, SP90, will170, level36.
Object pixel-like coordinates592,144 correspond to candidate tile18,4; cursor is18,4.
This corroborates the adjacent position while preserving the unverified map origin/dimensions.

Important negative: object+4/+6 is217/242, not boss descriptor indices29/51. Mech record+12
embedded index is zero. Neither field can be a universal identity rule. Object byte+1 is1
versus0 for the three checked allies, but one enemy is insufficient to establish side enum.

Combat fields do NOT match: offset-order M/R/evasion/accuracy/defense/skill raw values are
181/173/239/244/133/200; green screen values195/187/262/267/156/235. Differences are
14/14/23/23/23/35. Do not assume a bonus formula or expose raw fields as effective combat
stats. Systematic offline investigation is under `local/enemy-combat-values-20261015/`.
No production combat decoder or tactical binding was changed.

The existing offline inspect-map command successfully decoded named ally/enemy HP/EN/SP
from immutable extracted records. Private demo/config/provenance/report:
`local/ally-enemy-inspection-20261015/`. Assertions confirmed exact values, unknown
side/coordinates and false live/autonomous capability. This is a supplied-record demonstration,
not a live tactical snapshot. Next sample request index3; leave boss screen open until
asking user for a precise new enemy sample. No save/battle/controller input issued here.


## Taurus and Ally/Foe menu lead

User supplied Taurus/MobileDoll Unit screenshot and reports separate Unit Ally / Unit Foe
menus. Fresh sample3 selected mech descriptor08E67F08(index54), pilot08E6A700(index97),
relationship091C0C70 and object08E627D8; inspection records08E90770/08EA3ED4.
All14 checked values match: HP2603, EN49, DEF950, MOB100, HIT160, SP51, will114, level35,
M172/R172/evasion222/accuracy248/defense112/skill198. Object pixel-like position400,528
converts to12,16, matching cursor12,16. Duplicate selected globals agree.
Evidence: `enemy-taurus-validation.json` and `user-enemy-taurus-unit.png` in trial evidence.

Object byte+1 is1 for both checked enemies and0 for three checked allies. Grouping all27
referenced objects by that candidate marker yields21 zero and6 one. The six one-marked
objects are08E62158,08E627D8,08E62840,08E62DF0,08E62E58,08E62EC0. Membership/counts
remain hypotheses pending visible menu validation; separate menu screens do not prove
separate backing arrays (a shared collection plus filter is also possible).
Bounded pointer/list analysis is under `local/ally-foe-lists-20261015/`.
Next highest-value capture: Unit Foe list screenshot left open, to compare rows/counts and
before/after RAM rather than request many individual enemy screens. Next sample index4.

Boss effective-stat investigation corrected field ordering explicitly. Exact/regular-stride
searches for195,187,262,267,156,235 and delta14,14,23,23,23,35 found no corresponding
buffer in the retained dumps. Cause remains unresolved; no derived-stat formula or fix.
Taurus combat values match the raw fields, so mismatch is not common to both checked enemies.


## Foes menu correction: third party and inactive negatives

User checked menus:20 allies and5 foes. Wing Gundam Zero is in neither list; user explains
it entered this stage as a third party despite formerly being allied. Supplied Foes screenshot
shows allfive rows on page1/1. Sample4 captured with this menu open matches every HP/maxHP/EN:
Taurus2603/6600 EN49; Taurus4104/6600 EN50; Vayeate13393/24000 EN115;
Mercurius10507/26000 EN140; Euclid5211/9600 EN89.
Relationship pointers in screenshot order:091C0C70,091C0C80,091C0D70,091C0D80,091C0D60.
Evidence: `user-foes-list.png`, `foes-list-record-matches.json` and fullsample4.

The earlier21/6 object-byte grouping is explicitly RETRACTED as menu membership. Byte+1=1
includes the third-party WingZero; it cannot be decoded as enemy side alone. At object+14,
WingZero has0x401 while allfive listedfoes have0xC01, but a general rule still needs additional
stage/third-party/inactive negatives. One zero-byte-side object08E633A0 has HP0/max5300
and word+14=0; remaining20 objects havepositiveHP and word+14=1. That is consistent with
menucount20 but does not itself prove exact active membership or defeated-unit semantics.

Bounded menu-open RAM comparison found no direct five-entry row/object pointer array,
including regular strides4..256. The firstfour foe rows occur in a new stack sequence but
Euclid is separated by other rows and WingZero precedes it. Do not promote this stack data
to a foe list. Separate backing arrays versus filtered shared collection remains unresolved.
Private analysis: `local/ally-foe-lists-20261015/menu.json` and README.md.
Next valuable visible evidence: firstpage of Unit Ally, with tab leftopen, to identify the
menu's currentform/primarypilot row choices. Next sample index5. No production side or
complete deployment binding added. This correction supersedes prior candidate21/6 wording.


## Ally menu and usage-stop checkpoint

Sample5 corresponds to Ally page1/3. Allnine visible rows match HP/maxHP/EN and unique
objects, preserving aliases where form/primary-pilot choice was unresolved by resources.
Evidence: `ally-list-page1-record-matches.json`, `user-ally-list-page1.png`.
Selected Info globals remain at Taurus in both Foe and Ally menu captures despite Ally
highlighting Ptolemaios2. Never interpret those globals as the currently highlighted list row.
Descriptor+0 did not decode as direct name text; screenshot labels are supplied labels only.

Shared transient enumeration at09FFED28..09FFEDF8 (end exclusive) contains26eight-byte
(rowpointer,zero) entries,26unique objects. It is identical in samples4 and5. Filtering by
object word+14 gives20at0x1,5at0xC01,1at0x401. Firstnine0x1 rows reproduce Ally screenshot
order exactly; allfive0xC01 rows reproduce Foe screenshot order exactly. WingZero is the
sole0x401 entry. ZeroHP object08E633A0 is absent. Root independently reproduced these
checks; `root-menu-enumeration-validation.json` retains exact bounds. An initial root script
used the last-slot address as an exclusive bound and failed the count assertion; corrected
exclusive end09FFEDF8 passed. Do not copy ambiguous inclusive bounds from earlier notes.

This is strong shared-enumeration/filter evidence, not a proven durable reader root: stack
lifetime and general semantics remain unvalidated. Do not hardcode the stack address or
promote stateword enums across stages. Private agent evidence: `local/ally-foe-lists-20261015/ally-menu.json`.
Next work: find the stable owner/container or reproducible build path, corroborate remaining
11Ally rows if needed, validate another stage under approved protections, then review an
evidence-bound production extraction design before implementation. Keep existing tactical
runner disabled. No production code changed in this research continuation.

Usage reached8percent remaining, below user cutoff: substantial work stopped. Leave current
owned PPSSPP PID7868 open, no discard/reload. Helper execsession55588; next request6.
Current Ally firstpage is open; no new screenshot needed immediately. Recurring full-plan
job remains active every300minutes and must check allowance before resuming work.
