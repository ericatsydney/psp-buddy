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
