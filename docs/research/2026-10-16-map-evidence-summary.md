# Map evidence and next steps — 16 October 2026

This page separates working software from research evidence and remaining live gates.
The observations cover three maps, not thirteen different stages.

| Area | Established evidence | Remaining gap |
| --- | --- | --- |
| Offline candidate reader | Implemented and reviewed; strict bounded input, identity/code checks, all actor aliases preserved. 707 offline tests and static/build checks passed at the implementation checkpoint. | Supplied data is not authenticated live deployment. |
| Variable unit counts | The pool/catalogue join returns 69, 12 and 26 candidates in retained maps. | Future stages still need supported-layout/identity validation; counts are never constants. |
| Form and pilot representatives | The decoded source recipe reproduces cached representative sets in all 13 retained observations. A protected human Z Gundam/Waverider/return trial corroborates one live form lifecycle, with six matching observations. | Crew/stage/load changes remain unvalidated. Three retained observations have different list order. |
| Representative refresh code | A selector setter replaces an exact mech/pilot pair. Successful wrapper paths set the cache dirty flag. Separate descriptor-state handoffs also invalidate. | The full UI transaction and coupling between those paths are unproven. A clear dirty flag alone cannot establish coherence. |
| HP, EN and pilot statistics | Named inspection records match the previously supplied Unit screens. | The new structural reader intentionally does not choose a representative or aggregate stats. Effective boosted combat values are not universally decoded. |
| Map dimensions | Code-backed u16 width/height fields give 28×28, 34×26 and 24×34. Exclusive tile-lookup bounds and row-major indexing are identified. | Broader lifecycle/unsupported-layout handling remains research; production reports are unchanged. |
| Unit positions | Direct u16 tile X/Y fields at object +0x26/+0x28 feed the game grid lookup. All 107 retained pairs fit bounds; twelve match independently visible cells. Existing named-record CLI profiles report them correctly. | Supplied offline observations do not prove live completeness or movement legality; not all positions were independently visible. |
| Tile properties | Raw getters and a derived contextual classification builder are identified. A held-out state exposes ghost cells and missing current objects. | These cached classes cannot establish current occupancy, terrain, movement cost or legality. |
| Menu membership | Approved offline reader reproduces20Ally/5Foe/1outside across sixcaptures with existing stats/tiles. Fixed category parameters and objectbyte+0x15 mask filtering are code-backed. | Labels are supplied with evidence; tactical allegiance, thirdparty hostility, diplomacy and temporarycontrol remain unknown. |
| Capture and control | Protected known-record reads and supported Windows-menu screenshot collection have prior live evidence. | Unattended capture, current-screen recognition and calibrated battle menu recipes remain incomplete. |
| Action counter | A two-bit field has defined increment/decrement/init paths and now a verified End Phase “Unmoved Units” count path; retained counts reproduce 13/5/20. | Action consumption, phase ownership and legal Move/Attack commands remain unverified; a single bit is an invalid shortcut. |
| Planning and recovery | Offline planner/executor/checkpoint/supervisor contracts and synthetic scenarios exist. | Complete live tactical observations, legal-action evidence, live save/load backend and battle-MVP acceptance remain unverified. `run` stays disabled. |

## Current dependency

The user approved and completed the bounded human-assisted reversible form trial after fresh
complete SHA-256-verified backups. [The results](2026-10-16-representative-transition-validation.md)
show the same object selecting mech122/123/122, unchanged pilot/resources/positions and other
units, and the exact selector-pair change and restoration. The returned decoded stable
signature equals the starting signature. No more screenshots are needed for this trial.

The approved offline representative reader is implemented as an explicit descriptor kind,
separate from the structural reader. It reproduces69/12/26 candidates on retained maps and
all six form observations, reporting one source/cache-consistent representative and stats.
It does not add transformation actions. The separately approved positioned offline descriptor now adds validated tiles/dimensions,
matching107retained positions and allsix currenttrial captures. Live tactical integration
still depends on outstanding acceptance gates.

## Evidence locations

- [Counter, stale tile-cache and read-budget limits](2026-10-16-counter-and-tile-cache-limits.md).
- [Protected reversible form-change validation](2026-10-16-representative-transition-validation.md).
- [Map dimensions, direct tile fields and verified CLI profiles](2026-10-16-map-geometry.md).
- [Unit tables, representative source and lifecycle notes](2026-10-16-unit-table.md).
- [Offline retained-state comparison and visual checks](2026-10-16-offline-state-comparison.md).
- [Detailed map-inspection continuation](../superpowers/plans/2026-10-14-map-inspection.md).
- Private reproducible code/data: local/selector-lifecycle-20261016,
  local/cache-transition-paths-20261016, local/map-bounds-20261016,
  local/map-bounds-root-20261016 and local/handoff-bit-selector-20261016.

The later protected trial launched the isolated slot2 fixture and performed read-only
paused observations; the human supplied every navigation/transform input. The emulator
remains open, with no assistant battle/save/reload inputs. Production code and the Git index
were preserved. Research/workflow files remain uncommitted. The full707offline tests and
161focused integration/safety tests passed before launch, along with Ruff and type checks.

## Scheduled continuation — 17 October 2026

[End Phase count linkage](2026-10-17-end-phase-count.md) now traces the defining
aggregate into the fullwidth CP932 prompt strings. Mask1 is narrower than the Ally-menu
mask; a null resolved object also affects the inverse-zero helper and must fail closed
in a future reader. Independent offline review/reproduction passed. No production code,
emulator input or save changed. At this run's process inventory no PPSSPP process was
observed; earlier notes about an open process describe their historical trial only.
Next: evidence-bound counter inspection design, then causal action-transition validation
under its own applicable approvals and verified backups.

The approved offline End Phase counter reader is now implemented and independently
reviewed with no remaining findings. Full1078tests pass with1existingprivilege skip;
Ruff,mypy31sourcefiles,packagebuild and eight retained CLI reports pass. It adds
counter_value,EndPhase scope and raw/displayed unmovedcounts; all live flags remainfalse.
Next dependency is causal action consumption and phase/legal-command evidence, not
additional form/position/menu/counter-field searches. No emulator operations or commits.
