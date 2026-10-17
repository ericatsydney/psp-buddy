# Read-only map inspection implementation plan

## Continuation, 15 October 2026

Resume authorized implementation with the existing approved design. The five-hour session
goal is reliable current capture followed by visibly corroborated deployment/coordinate
bindings and a held-out reload check. Keep partial/unknown fields explicit and leave
autonomous battle execution disabled. Stop below10% remaining account allowance.

- [x] Check status/recent commits: only prior authorized implementation/workflow changes.
- [x] Rerun baseline:603 offline tests, Ruff and strict mypy pass.
- [x] Independent whole-working-tree review: no Critical/Important findings. Correct Minor
  historical documentation contradictions. Existing core/CLI feature is review-complete.
- [x] Fresh protected capture trial with process-exit diagnostics and supported observed
  menu keyboard navigation if click geometry is unavailable. No automatic cursor input.
- [x] If fresh frames work, sample broad RAM under bounded coherent observation scopes,
  correlate reversible cursor/info changes, and distinguish cursor from deployed-unit fields.
  Three horizontal samples plus five samples after a separately backed-up reload establish
  cursor-related X/Y candidates and named status-panel correlation, not deployed-unit positions.
- [ ] Validate candidate unit identities/side/positions against visible allies/enemies and
  inactive negatives. Reload in a separately backed-up trial before operational binding.
- [ ] Update evidence/profile/reader tests only for corroborated fields; run affected and
  full checks, review changes, capture results and record remaining gates.

Source investigation found raw-pixel base64 versus PNG URI mismatch in MCP0.2.0 screenshots;
do not trust its image/png block as a decoded image. Retain Python's existing URI allowlist
and the verified file collector while investigating native capture availability.

### 15 October handover

Baseline 603 offline tests, Ruff and strict mypy pass. Final independent review of the prior
inspection feature is complete with no Critical/Important findings; Minor historical-doc
contradictions were corrected. No production source changed in this continuation.

- Native Windows frame capture still times out. Observed keyboard selection of Debug >
  Take screenshot produced valid 944x541 built-in JPEGs: three in trial
  `20261015T012546647014Z-21454d99fc34438b84254e5277322275`, five in reloaded trial
  `20261015T013217147892Z-d310387778964f1b96254e5b7fc2f641`.
- Each accepted frame has a complete 24 MiB RAM sample gathered under a bounded pause scope.
  First trial stopped on a research action-file publication race; second used atomic rename.
  Both closed owned PPSSPP and passed original/configuration/snapshot/archive preservation.
- Cursor-only horizontal ABA samples: u16 `0x096007C4` = 17/18/17 and
  `0x096007C8` = 560/592/560. Reloaded vertical ABA samples: `0x096007C6` = 4/5/4,
  `0x096007CA` = 144/176/144. These track cursor-related tile/spatial state; camera/origin
  and absolute map interpretation remain unverified. Never bind them as unit positions.
- Named status panel corroborates Gundam 00 / Setsuna, HP5000, EN121, level36, will150.
  Cross exposed a status panel, not the command menu. The prior successful Info recipe
  used Circle to confirm. Do not reuse the mistaken Cross/Up sequence as a menu recipe.
- Installed MCP probe in the second trial returned code0 and matched both retained named
  records. The research helper then raised UnicodeEncodeError while printing the Japanese
  title through a cp1252 console. Final preservation still passed. Use Python `-X utf8` for
  future trial commands; do not repeat a live trial solely to test console encoding.
- Two unchanged 132-row relation-table copies were found near `0x09601B20` and
  `0x096027F0`; their semantics and deployment status are unproven. Do not promote IDs from
  coincidental stat matches. Private analysis: `local/cursor-diff-20261015/`.
- Last usage check was12% remaining; finish handover and stop below10%. No further live
  trial is started. Full live map acceptance remains incomplete.

Resume with the known Circle-confirm information recipe, visibly correlate selected unit
IDs against broad RAM, distinguish deployed units from reserves, and validate actual unit
positions/side/action status after another protected reload. Capture remains interactive;
standalone unattended triggering and complete tactical observation are separate gates.

> Execute bounded tasks with disjoint agent write scopes and review before dependent work.
> All files remain uncommitted. Written design approved by the user on 14 October 2026.

**Goal:** Inspect corroborated battle-map data safely; report unavailable deployment/map fields
explicitly until protected live evidence establishes their layouts.

**Architecture:** Keep offline inspection separate from tactical Snapshot. Decode bounded
explicit record layouts into immutable named records, with user-supplied evidence provenance.
Protected discovery uses existing launch/backup/debugger services and the installed MCP;
neither an offline descriptor nor a plausible byte pattern authenticates a deployed roster.

**Stack:** Existing Python/Pillow/websockets/pytest/Ruff/mypy; installed local MCP 0.2.0
and Node 24 for private research only. No new production dependency.

**Spec:** `docs/superpowers/specs/2026-10-14-map-inspection-design.md`.

## Task 1: Discovery and baseline (root; private research only)

- [x] Check status: only current authorized plan/assessment/MCP configuration changes.
- [x] Run baseline: 545 tests, Ruff and strict mypy pass. Windows sandbox pytest temporary
  directory denial requires unrestricted offline runs; preserve diagnostics.
- [x] Analyze preserved RAM: 0x50 stat/form-table stride is a structural candidate, not
  deployment. Existing 0x08E90000 samples are invariant; broader differential samples needed.
- [x] Create and verify fresh original/portable save/configuration snapshots before isolated
  capture trial. Trial stops with owned process gone before accepting a frame; no game input,
  raw memory sample or MCP probe obtained. Final original/snapshot/archive preservation passes.
- [x] Separate freshly backed-up memory-only trial: verify installed MCP reads equal the
  protected Python named mech/pilot records, exact known stats and output lengths. Preserve
  evidence privately, close both clients and owned emulator, and recheck source hashes.
  Trial `20261014T084029300668Z-0ffa88aef38c4ed4995759d13921def4` passed with HP5000/5000,
  EN121/210, SP55/95, level36/will150. Final source/snapshot/archive preservation passed.
- [ ] Resume reversible cursor/info discovery only when supported capture yields fresh frames.
  Corroborate deployment/coordinates/side/action state and held-out reload before live claims.

## Task 2: Offline map inspection core (agent write scope)

**Create:** `src/psp_buddy/map_inspection.py`, `tests/unit/test_map_inspection.py`.
No edits to models/profile/reader/CLI or other tests in this task.

Define immutable `MapField(name, offset, width, evidence_ids, meanings=())`,
`MapRecordProfile(label, address, size, fields)`,
`MapInspectionProfile(game_id, patch_id, emulator_version, map_label, dimensions, records)`
and `decode_map_inspection(profile, samples, game_id, patch_id, emulator_version)`.
`samples` is an immutable tuple of bytes corresponding exactly to explicit profile records.
Return frozen report/record values, missing fields and `named_records_only` completeness.
Do not construct tactical Snapshot or imply deployment/live authentication.

Allowed fields: unit_id, hp/max_hp, en/max_en, sp/max_sp, x/y, side and action_available.
Widths 1/2/4; unsigned little-endian; max 64 KiB per record, 256 records, 1 MiB total.
Require nonempty bounded unique record labels, addresses in PSP user RAM, nonoverlapping
record windows, no duplicate/overlapping/out-of-bounds field layouts, and bounded nonempty
unique evidence references. Dimensions are either None or integer width/height in 1..1024.
Coordinates require both x/y and dimensions; decode rejects out-of-map values. side meanings
are explicit unique raw-value mappings to ally/enemy/neutral; action meanings are explicit
raw mappings to available/spent. Reject unmapped raw enums; never assume default encodings.
Reject invalid HP/resource maxima, duplicate decoded unit IDs and bool-as-int inputs.
Unknown fields remain None; decode identity/sample-length mismatches fail closed.
Evidence references are user assertions, not authenticated verification.

- [x] Write synthetic acceptance/rejection tests, run focused pytest and observe meaningful
  missing-feature failures before production code. Include a partial named-stat record that
  produces unknown position/side/SP/action, and complete synthetic coordinates/enum layouts.
- [x] Implement only this inspection contract. Run focused tests green; refactor with tests
  passing. Add tests for invalid dimensions, mutated samples, malformed enums, duplicated IDs,
  wrong bytes/identity, resource bounds and all profile size/overlap limits.
- [x] Agent runs Ruff/mypy for its module and reports red/green evidence; root reviews API,
  invariants and spec compliance before Task 3 starts.
  9 focused tests pass. Root review corrected EN/SP zero-capacity semantics with a failing
  behavioral regression test; HP maximum remains positive. Unknown-field reports stay explicit.

## Task 3: Strict offline descriptors and CLI (root or separate bounded agent)

**Create:** `src/psp_buddy/map_inspection_io.py`, `tests/unit/test_map_inspection_io.py`.
**Modify:** `src/psp_buddy/cli.py`, `tests/unit/test_cli.py`, `docs/usage.md`.
Descriptor kind `map_inspection`, schema_version 1; exact keys reflect Task 2's public
dataclasses. A separate records manifest supplies a local file for each exact profile record
in profile order. Reuse bounded file reads, duplicate-key and finite-number JSON rejection.
Resolve relative record files from the manifest directory. No bytes are fetched from emulator.

- [x] Write rejection tests for unknown/missing keys, wrong identity/schema/kind, duplicate
  names, invalid field/enum types, manifest count/order mismatches and oversized/truncated files.
  Run focused tests red before parser implementation.
- [x] Add `inspect-map --config PATH --records PATH`. Dispatch before existing stat-profile
  parsing; use config.profile_path for the map descriptor. Require records explicitly, with
  no live imports, sockets, launch, input or save fallback. JSON reports supplied provenance,
  false live authentication, false autonomous availability, named records, unknown fields and
  incomplete deployment/terrain/phase/legal-action status. Existing commands remain unchanged.
- [x] Run focused CLI/parser tests green, then full verification and CLI demo on synthetic
  fixtures and retained named-record evidence. `run` must continue to refuse execution.

## Session handover, 14 October 2026

- Verification: 603 offline tests pass; Ruff and strict mypy (21 source files) pass; wheel
  builds; CLI help and retained MCP record demo pass; run refuses live execution; diff check
  passes. Restricted pip build failed on its temporary tracker permissions, then unrestricted
  build passed. CLI/parser focused suite had71 passes after meaningful red failures.
- Actual protected MCP/Python record equality and known stats passed; original/snapshot/archive
  preservation passed. Supported capture trial failed before any accepted frame or game input.
- Core task root review passed after the zero-capacity EN/SP regression fix. Final independent
  whole-working-tree review is still pending; no final code-review completion claim is made.
- Full map milestone remains incomplete: no validated deployed roster/side/coordinates/action
  state, no held-out map/reload binding and no reliable current capture for differential research.
- Latest usage check reached10% remaining. Preserve this checkpoint and stop once below10%.
  No further emulator trial or major task is started. All files remain uncommitted.
- Retained offline demo: `local/map-demo-20261014/report.json`, produced by
  `inspect-map --config local/map-demo-20261014/config.json --records local/map-demo-20261014/records.json`.
  This reports named mech/pilot records separately, never a deployed-unit join or tactical map.
- Resume order: final whole-working-tree review and blocking fixes/checks; investigate supported
  capture availability in a new freshly backed-up trial; then reversible broad RAM comparisons
  and held-out corroboration before promoting any deployment/map binding.

## Task 4: Verification, review and handover (root)

At every task/trial boundary read account usage. Stop further work below 10% five-hour
remaining; close owned processes, preserve evidence and report outstanding tasks.
Use unique local basetemp names for each invocation; never delete prior trial evidence.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_map_inspection.py -q -p no:cacheprovider --basetemp local/map-core-20261014
.\.venv\Scripts\python.exe -m pytest tests/unit tests/scenarios -q -p no:cacheprovider --basetemp local/map-full-20261014
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src
.\.venv\Scripts\python.exe -m pip wheel . --no-deps --no-build-isolation --wheel-dir local/map-wheel
.\.venv\Scripts\python.exe -m psp_buddy --help
git diff --check
git diff HEAD
git status --short
```

Expected: offline tests/checks/build pass; inspect-map reports unknowns honestly; run refuses.
Review tracked and intended untracked files against the spec, fix Critical/Important findings,
rerun affected checks and review again. Record live failures and source preservation results.
Foundation/tooling completion does not mean full battle-map acceptance; if no deployment
binding is validated, the live map snapshot milestone remains incomplete.


## Selected Info record research, 15 October 2026

Protected manual handoff trial `20261015T065827988941Z-c31825d738e445cc9db4e7fa0ceb0173`
retains full RAM samples and screenshots under its `user-evidence` directory. The emulator
remains open at the user's request; these samples are one continuing protected session.

- Same-process Shenlong -> Gundam 00 -> unchanged Gundam 00 -> Shenlong reversal passed.
- Candidate selected mech chain: `u32(u32(0x08E60674) + 4) + 0x10`.
- Candidate selected pilot chain: `u32(u32(0x08E60678) + 4) + 8`.
  Duplicate globals at `0x08E60680/84` corroborate both chains.
- Held-out third robot Dancouga Nova/Aoi passed all 14 visible checks: HP5782, EN9,
  DEF1650, MOB70, HIT145, SP44, will150, level33 and six pilot combat values.
  Records resolved to `0x08E95040` (mech) and `0x08EADC0C` (pilot).
- Descriptor tables remained stable while selected pointers changed. This supports selection
  through pointers; it does not prove the complete deployment list's order or semantics.
- Evidence: `selection-pointer-reversal.json` and `third-unit-pointer-validation.json`.
- These are research candidates for this build/stage/process, not production bindings.
  Next: confirm reload stability, then a different stage. Separately establish deployment,
  side and world coordinates before claiming a tactical map. No further screenshot of these
  three units is needed unless a specifically identified unresolved value requires it.
- Research helper disables WebSocket automatic pings diagnostically; read failure retains
  the user's window. No root-cause claim or production transport change follows from this.


Continuation checkpoint: selected combined relationship globals08E6067C/88 validated
across all five samples; relationship lists remain selection-invariant. See
`docs/research/2026-10-15-selected-unit-memory.md`. Restart remains pending user confirmation
of PPSSPP unsaved-progress exit warning. No production code changes in this research step.
Usage11% remaining; no new major task started. Current window remains at exit prompt.


## Recurring full-plan continuation, 15 October evening

User authorized resuming now and every five hours across the entire approved MVP plan,
not only deployment/coordinate research. Automation `resume-psp-buddy-implementation` now
uses a300-minute interval and reads current plans/state before choosing unfinished work.
Its safeguards preserve user edits and prohibit commits/publishing; new scope still needs
its applicable design review. Historical checked continuations supersede stale unchecked
boxes in the original MVP plan; do not rebuild completed generic runtime components.

The previous manual handoff process exited before this continuation. Its helper reported
`PRESERVATION_VERIFIED: originals/snapshots/archive unchanged`; no process was found.
User explicitly approved a fresh protected slot-2 launch after being told of that exit.
The restricted process inventory failed closed before any launch; the same protected
launcher was then started outside the sandbox to retain the normal non-writing/backup gates.
Do not infer that this approval permits later discard/reload of a newly unsaved session.

Offline discovery now finds descriptor rows aliasing104-byte objects with candidate pixel
coordinates. Keep them research-only until visible map, reload and negative examples validate
membership/meaning. Evidence lives under `local/position-object-research-20261015`.


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


## Scheduled continuation, 16 October 2026

Code-backed unit-table discovery and14-sample checks are recorded in
`docs/research/2026-10-16-unit-table.md`. Base08E61F50,224slots,stride104.
This provides a durable build-specific root beyond the transient stack, but remains research-only
until other-stage and active-form/primary-pilot validation. Preserve staged user edits.
Current process inventory finds no PPSSPP; old PID7868 ownership checkpoint is stale.
No emulator launch/control/reload, production changes or commits in this continuation.


Offline other-map continuation: existing manifest-verified slot1 states were extracted without
emulator use. See `docs/research/2026-10-16-offline-state-comparison.md`. Code-defined pool
layout matches; candidates69and12 versus26fixture. Portable thumbnail independently matches
all12predicted occupied cells, cursor excluded. This is structural/relative-position evidence,
not full tactical acceptance. No new save-state material required immediately. Current-form/
primary-pilot linkage and complete affiliation/bounds validation remain before production.

Bounded actor-owner/catalogue joins now reproduce69/12/26 candidate objects across three
retained map states, preserving all91/12/56 actor aliases. Per-object counts match occupancy
references. Primary-pilot shortcuts failed held-out data and remain rejected. A structural
reader can proceed independently of unresolved tactical semantics, subject to written approval.
Proposed extension: docs/superpowers/specs/2026-10-16-unit-pool-inspection-design.md.
Independent spec review found three Important interface omissions; all were amended and
re-review reports no Critical/Important findings. Minor alignment wording also clarified.
Next dependency: user review of this written extension, then exact implementation plan and
bounded TDD for pure decoder plus strict IO/CLI. Do not implement before approval. Existing
research and staged user work remain uncommitted. No emulator actions were performed.

User approved the16October structural-inspector design. Implementation and validation are
complete; see2026-10-16-unit-pool-inspection.md. All707offline tests, Ruff, strict mypy and
wheel build pass; final independent review has no findings. Production bounded decoder
reproduces69/12/26retained candidates and all91/12/56aliases, without full-RAM scanning.
The exact documentation example also works through the real CLI. Existing named-record
output remains covered. Saves/emulator untouched; no commits. This supersedes the preceding
pending-approval checkpoint. Tactical/live gates and unresolved form/crew semantics remain.

Post-implementation offline research found a separate cached representative list, exactly
one actor per object in all13retained observations across the3maps; all selectedInfo links
match. See cached-representative section in2026-10-16-unit-table.md and its private reproducers.
The prior header+0E hypothesis is rejected as a universal current-form selector: Allymenu
has26cached representatives but only20marked headers. Query code extracts bits2..5 of
header+3C and rewrites marks according to supplied filter. No production selection logic
was added. Next research: source builder089230E0 and invalidation/lifecycle of08ECF708;
do not repeat screenshots or promote cache representatives to universal primary pilots.

16October continuation: source builder089230E0 is decoded. Two-phase source selection plus
corrected mech/pilot exclusion reproduces cache SETS in all13retained observations, with
69/12/26 representatives. Order matches10/13; no menu-order promise. Pair-exclusion record
layout was corrected to+4mech/+0x10pilot; old private analysis regenerated. See latest
2026-10-16-unit-table.md sections and local/representative-source-20261016 reproducers.
Dirtyflag lifecycle traced statically: bitclears before rebuild, so clearbit cannot establish
coherent freshness. Owner creation/teardown and generic mutation invalidation are known,
but specific transform/deployment/stage/load behaviour remains unverified. Next bounded
work: precise lifecycle tracing or protected before/after validation, then written design
review before any representative-selection production extension. No emulator actions,
production edits, commits or repeated screenshots. Existing implementation checks stay707.
Independent read-only research claim review found no material corrections:13matching sets,
10matching orders, corrected exclusion offsets and cache-coherence limits all agree with
retained scripts/findings. Repository diff whitespace checks pass. No new implementation
approval is requested until lifecycle evidence supports a concrete representative contract.

Final bounded read-only continuation:20of62candidate flag-store windows contain an explicit
LUI(base,08B4) followed only by recognized immediate/load instructions that do not clobber
that base before SB(+7D2F). This strengthens local effective-address evidence for these
instruction sequences, not all-path runtime execution or gameplay semantics. No production
or emulator changes. Allowance check reached9percent remaining, below10percent rule;
substantial work stopped. Reported reset:16October2026 at12:02:21AEST. Resume lifecycle
tracing or protected transition validation after reset; do not repeat the completed source
selection reconstruction or representative-set comparisons.

Noon heartbeat allowance reset after initialcheck; repository unchangedfromauthorizedwork,
no runningPPSSPPprocess. Selectorreplacement/cacheinvalidation path identified and private
reproducers retained. A human-assisted reversible form-change trial design was written and
reviewed; awaitsuserapproval, becauseapproveddiscoveryinputscopeexcludesformchanges.
Spec2026-10-16-representative-transition-trial-design.md (no helperimplementation/launchyet).

Independent map research closed a separate gap: width/height areu16at08E52A94/96; dimensions
28x28,34x26,24x34. Directunitobjectu16+26/+28 aretileX/Y, fed into the game'srowmajorlookup.
All107objects checked;12visiblepairs match; originalG00/WingZero(17,4)/(18,4) matchuseradjacency.
Existingnamed-recordCLI verifiedall69/12/26coords usingprivateprofiles, no productionchanges.
Allcapabilitiesfalse; unitidentity/side/resources/actionremainunknowningeometryreports.
Independentreviewfoundnomaterialissues; evidenceIDcitationfixedandCLIrerun. Seegeometrydoc
and2026-10-16-map-evidence-summary.md. Conditionalcell+Efailsuniversaloccupancy; terrainnotdecoded.

Further bounded independent work: found2bitcounter(objectbyte8>>3)&3 withactualinc/dec/init,
includingability-entryID27conditionforvalue2. Originalraw1positive13matchesvisibleUnmoved13,
butUIcountcouplingunproven; action_available staysunknown. Rawbit3alonewrongforvalue2.
Derivedcellbyte9buildercontextual:portable3activepositionsnotclass2/4 plus6ghostclass2/4cells,
withcontextactorobjectnull. Rejectthiscacheascurrentoccupancy/terrain/legalitysource even
thoughcurrent26happenstomatch. See2026-10-16-counter-and-tile-cache-limits.md andprivate
reproducers. Targetedreadspanbytebudgetsrecorded, notimplemented/livebenchmarked.

Allnew geometryclaims reviewed; existingCLI profiles ran107recordcoordinates withfalse
capabilities, no productioncodechanges. Newsummary2026-10-16-map-evidence-summary.md explains
workingsoftware/evidence/unknowns. Reversibleformtrialdesignapprovalremains pending; no
launch/helperimplementation/gameinputs. The nextdependentlive task mustwaitforapproval;
furtherauthorizedofflineinvestigationmaycontinuewithoutrepeatingcompletedfieldsearches.
Research-handoverreviewcompleted: no material corrections to2bitcounterlimits,3missing/6ghost
contextualtile-cachecells, orqualifiedread-budgetestimates. Directtile-coordinateevidence
remainsseparate/positive. Plain-languageprogresssummaryopened(queued)inthischat. Thehuman
formtrialapprovalquestionremainspending; no newinputsareauthorizedbyelapsedtime. Future
runscheckforreplybeforewritingtrialhelperorlaunching. Otherofflineworkcanaddressstatic
mapmetadata/terrainorEndPhasecountercoupling; donotrepeatcompletedrepresentative/geometry
searches. No emulatorprocessobservedatfinalinventory; existingcode/index/savespreserved.

## Affiliation continuation — 16 October 2026

User approved offline side research after positionedreader completion. See new
research/2026-10-16-affiliation-query-groups.md. Verified237row rawobject/header group
correlations, current20/5/WingZero1 acrosssixstablecaptures. StaticUI listpredicate traced
frommenuinitializer throughobject+15 shiftmask, staticcategory masks000F/F000/00F0/0F00;
currentcategorycounts20/5/1/0; original24/25/20/0;portable8/4/0/0. Nine exactcodewindows
matchbothcleansources. No production sideenumorcapability promoted; no emulator operation.
Nexttrace categoryparameterproducer and visiblelabels, then prepare readerdesign; keep
thirdpartyhostilityunknown. Private scripts/output local/affiliation-query-20261016 and
local/affiliation-research-20261016; no needrepeatcompletedcoordinate/form/rostersearches.
Currentfivehourusage87%used atlastcheck; stopsubstantialworkbelow10%remaining.

## Scheduled continuation — 16 October 2026,22:02AEST

Allowance reset verified (0%used atstart). Currentrepository matches authorizeduncommitted
work; PPSSPP PID14684 remainsopen and was not controlled. Bounded offline producer tracing
resolved fixed categoryparameters: four20byte records [16A,-1,category,0,0], count-skipping
loop opens type6UI. Do not equate UIpoolindexwithcategory (emptycategories compacted).
Independent retainedFoe/Ally samples expose 20/5/1 filteredlists and switch activeinstance
state between foe/ally lists, corroborating screenshotlabels. New detailed evidence appended
to research/2026-10-16-affiliation-query-groups.md; rawprivate code remainsignored.
Next: prepare scoped offline menu-membership reader design/plan for writtenreview, reporting
observed Ally/Foe membership separately from unknown thirdparty hostility. No production
code before new writtenapproval. No further form/position/count screenshots needed. Keep
currentemulator open; no reconnect,newtrial,save,reload or auto-close.

## Proposed implementation boundary prepared

A concrete offline menu-membership design and plan are saved as
specs/2026-10-16-menu-membership-inspection-design.md and
plans/2026-10-16-menu-membership-inspection.md. They require new written review before code.
The reader will expose Ally/Foe menu membership and outside-both status using explicit
profile label mapping and captured masks. It will retain unknown tacticalside/hostility
and allfalsecapabilities. Unsupported rawgroup values outside0..15 reject rather than
silently apply wrappedshift behavior. The immutable expected mask-table fingerprint uses
existing semantic-overlap protection; old APIs remain unchanged. No further screenshots
or live inputs are needed for this offline extension. Do not implement before approval;
independent authorized offline action/terrain research may proceed while awaiting a reply.

Independent proposed-design review found no material contradictions or missing gates;
composition works with existing immutable APIs, exact mask-table fingerprint and combined
geometry/recipe limits. Written user approval remains pending. Allowance18%used at final
boundarycheck; no usage cutoff or emulator action. No changes committed.

## Approved menu-membership extension complete

Userapproved written design;1010tests pass1existingprivilege skip,Ruff,mypy29src,wheel/help,
privateeightcaseCLI and independentreview pass. Source/menu_membership_inspection.py andIO
plus newCLI kind retain selectedstats/tiles, reports20Allymenu5FoemenuWingZerooutside on
sixcaptures. No tacticalside/hostility inference,allcapabilitiesfalse. No appoperationorcommit.
Exactcompletedplan:2026-10-16-menu-membership-inspection.md. Next actionavailability UIcount/
phase semantics or legalactionevidence in dependencyorder; no need repeatmenu/form/position
work. Privateverification exports explicitstaticcode/tablecompositeprovenance. Original user
stageddocs/index and ongoinguncommitted changes preserved. TransformactionsexcludedMVP.

## Scheduled continuation — 17 October 2026,07:54AEST

Offline action research found the actual End Phase UnmovedUnits count path.
See research/2026-10-17-end-phase-count.md. Aggregate0888449C queries mask1, counts
inverse resolved-object zero-counter tests, and UI08878B94 formats that count beside
CP932 fullwidth UnmovedUnits:/unit/s and End phase?. Exact code/data windows match both
clean retained states; independent resolver reproduction gives original13,portable5,
current20. Counts are actors, not summed counter values. Display wraps modulo100.
Null resolution and mask1 versus Ally-menu scope are explicit limits. Independent review
found no blocking issue. No general action_available, phase ownership, legal Move/Attack
or causal consumption semantics is promoted. No production edits/tests or emulator actions
were needed; original staged files and all authorized ongoing edits remain preserved.
No PPSSPP process observed in current inventory; do not relaunch/reload automatically.
Next bounded task: prepare written offline counter-inspection design/plan for user review,
then implement only within that approved scope. Retain action/terrain/live acceptance
gates and no Transform actions. Do not repeat completed menu/form/position research.

## Approved End Phase inspection implementation — 17 October 2026

Writtenapprovalrecorded; purecore/strictparser/newCLIkind implemented with68newtests.
Full1078pass1existingWindowsprivilegeskip,Ruff,mypy31src,wheel/help/diffpass.
EightretainedCLIcases reproduce13/5/20andpreserveoldstats/tiles/menurows. Code/text
fragmentsareexplicitofflinecomposites. Reviewerfoundpoolinclusiveanchorbudgetgap;
failingregressionthenfixenforcesglobal32/16KiBunion. Noappoperationorcommit.
Exactplan:2026-10-17-end-phase-inspection.md. Nextcausalactiontransition/phaseandlegal
command evidence requiresitsownwrittenprotectedtrialscope; do notrepeatcompleted
counter/UI/position/menu/formsearches. Transform remainsoutsideMVP; run remainsdisabled.

## User MVP scope revision — 17 October 2026

Player-unit actions are Move and/or Attack only. Spirit (including Trust), Repair, Supply,
Transform and crew changes are excluded. Earlier healing research/tasks are historical and
not current MVP requirements. Existing turn/reaction controls remain under prior gates.
Next offline change is planner plus executor enforcement, specified in
specs/2026-10-17-move-attack-mvp-design.md, pending written review before production edits.
No new support-action research or emulator inputs are authorized by this scope revision.

## Approved Move/Attack MVP enforcement complete — 17 October 2026

Repair=healingandTrustselectionremoved; unknownhealing/SPfieldsnolongerblockvalid
Move/Attack/retreatplanning. ExecutorrejectsRepair/Trustbeforeobserve/recipe/send,
withcleanupreleasepreserved. HP-retreat,targeting,resources,freshlegalityandexisting
turn/reactioncontrolsunchanged. NoSupply/Transform/Spiritfeatureadded. Full1078tests
pass1existingprivilegeskip,Ruff,mypy31,wheel/help/diffpass. Noappoperationorcommit.
Nextdependency: concretewrittenprotectedMove/Attackhuman-assistedtrial, thenapproval
before any newlaunch/load/battleinput. Countersaloneare notlegal-actionevidence.
Exactapprovedscopeandresults:2026-10-17-move-attack-mvp.md.

## 17 October JIT fingerprint diagnosis and quota stop

Actualforecastfailureidentified:0x088A2AAC64-byteanchor has2PPSSPP RUNBLOCK
markerwords;remaining56bytesmatch. Supportedoriginalcodeview needed, notmasked
fingerprints. See research/2026-10-17-move-attack-trial.md andplan
2026-10-17-original-code-read.md. Scopedadaptermethodimplementedwith46focused
tests/Ruff/modulemypy pass, but independentreview/fullsuite/privateintegration/live
validation PENDING. Stopsubstantialwork91%five-hourused/9%remaining. PID4496open
atEuclidforecast,helper3492disabled, noStart/reconnect/close/replay/commit. Continue
fromthishandoverafterallowancereset,donotrepeatcompletedform/menu/positionresearch.
