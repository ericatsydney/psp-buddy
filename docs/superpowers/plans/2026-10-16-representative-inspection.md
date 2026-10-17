# Offline representative inspection implementation plan

> For agentic workers: use bounded disjoint tasks and independent review under AGENTS.md.
> Written design approved by the user on16October2026; execute within its offline scope.
> No commits, pushes, emulator inputs, reloads, closure or new trials.

**Goal:** Decode one source/cache-consistent representative per candidate object and its
corroborated stats from explicitly supplied offline memory spans.

**Architecture:** New immutable pure decoder and strict IO descriptor, dispatched through
the existing inspect-map CLI. Reuse structural candidate validation without changing old
contracts. No live fetcher, tactical Snapshot or automatic capability promotion.

**Tech stack:** Python3.11+, dataclasses, hashlib, pathlib, pytest, Ruff, mypy, setuptools.

Design: `docs/superpowers/specs/2026-10-16-representative-inspection-design.md`.
Baseline: 707offline tests,161trial/private safety tests passed before this design work.
All pre-existing staged/unstaged files are authorized ongoing work. Preserve them.

## Task1: Pure profile, spans and recipe (core worker)

Files: create `src/psp_buddy/representative_inspection.py` and
`tests/unit/test_representative_inspection.py`. Read existing structural decoder/profile.
Use only synthetic fixtures in public tests, no copied private bytes/addresses/hashes.

- [x] Write fixtures for a small supported104-byte pool,16-byte catalogue, two distinct
  form actors for one object, a different object,12-byte nodes, descriptors/metadata/stat
  records,90selector pairs,154blocked IDs and127exclusion records. Use a synthetic code
  anchor with its calculated hash. Helper `sample(form=122)` returns `(profile, spans)`;
  `report(form)` calls the pure decoder with explicit profile identity.
- [x] Observe missing-module red with `.venv/Scripts/python -m pytest
  tests/unit/test_representative_inspection.py -q`. A first behavioral test must assert
  one representative per object and preservation of the correct selected form/pilot:

  ```python
  profile, spans = sample(form=122)
  result = decode_representative_inspection(
      profile, spans, profile.pool_profile.game_id,
      profile.pool_profile.patch_id, profile.pool_profile.emulator_version)
  row = result.to_dict()['representatives'][0]
  assert (row['mech_id'], row['pilot_id'], row['hp'], row['defense']) == (122, 134, 4700, 1000)
  assert result.to_dict()['autonomous_available'] is False
  ```

- [x] Implement frozen `RepresentativeInspectionProfile`, result rows and report with
  exactly the spec fields. Validate direct Python construction as strictly as JSON:
  tuple/type/bool/range/address/capacity/anchor/evidence/overlap checks. No I/O imports.
- [x] Implement bounded contiguous reads; obtain a covering subset of at most11spans for
  the old structural decoder, preserving its32span limit. New validation accepts128spans
  with unchanged64KiB/per-span and1MiB total limits. Test required windows crossing a gap.
- [x] Implement exact source chain, bounded source/cache traversal, catalogue membership,
  descriptor IDs, two-phase selection and enabled pair exclusions. No order semantics.
  Require source/cache SET equality and complete unique object coverage before stats.
- [x] Add parametrized red/green cases for cycle/duplicate/off-region nodes, capacity,
  unknown catalogue actor, invalid object slot, null candidate descriptor, descriptor
  misalignment/out-of-region, missing metadata/header, malformed IDs, unsorted blocked
  IDs, duplicate reconstructed actor, ambiguous pair, and stale/missing/extra cache rows.
  An unused/absent pair follows the observed recipe exactly; test both explicitly.
- [x] Decode fixed mech/pilot stat windows with resource bounds. Test HP>maxHP,
  maxHP0, EN>maxEN, truncation; SP is raw current SP with maximum unavailable.
- [x] Add same-object/pilot122->123->122 synthetic round-trip assertions, with changed
  selected actor/record and DEF/MOB but restored result, plus unchanged other object.
  Test69/12/26-like variable synthetic counts and a truly empty valid report.
- [x] Test deterministic sorting, exact serialization fields, required false flags and
  unavailable fields. Verify mutable input collections/overlapping spans/identity/code
  mismatches reject. Run focused pytest, Ruff and strict mypy for this module. Root
  reviews before IO/CLI depends on its finalized constructor/signatures.

## Task2: Strict descriptor and files (IO worker, disjoint scope)

Files: create `src/psp_buddy/representative_inspection_io.py` and
`tests/unit/test_representative_inspection_io.py`. No CLI or core edits in this task.

- [x] Write failing tests for `parse_representative_inspection_profile(values)` and
  `load_representative_spans(path)`. Observe missing-module red. Use complete synthetic
  JSON descriptors containing the nested unchanged structural descriptor.
- [x] Implement exact key/kind/version parsing using existing bounded JSON helpers and
  nested structural profile parser. New manifest kind representative_spans accepts
  1..128entries; do not modify old manifest parsers or their limits.
- [x] For every integer field test bool,negative,oversized and misaligned values;
  reject duplicate/unknown/missing keys,nonfinite numbers and bad anchor/evidence values.
- [x] Test manifest-relative paths, regular immutable file reads, missing/truncated/
  oversized/changing files, symlinks/hardlinks/special files, overlapping address windows,
  per-file64KiB and aggregate1MiB limits checked before retaining data. Poison the read
  helper to prove oversized aggregate input is rejected before binary loading.
- [x] Test wrong manifest kind in both new/old directions; new128-entry allowance must
  not change old32-entry rejection. Run focused IO/core tests, Ruff and mypy.

## Task3: CLI and documentation (root after reviewed core/IO)

Files: modify `src/psp_buddy/cli.py`, `README.md`, `docs/usage.md`; create
`tests/unit/test_representative_cli.py`. Preserve all existing uncommitted CLI/docs work.

- [x] Write failing inspect-map tests for new descriptor dispatch, stable JSON result,
  no records argument, config/profile identity mismatch before binary reads, and invalid
  cache/coverage producing status2 rather than partial JSON or fallback.
- [x] Implement dispatch before existing strict parsers, using new IO and pure decoder;
  retain standard configuration metadata and fixed capability fields. Add help text
  without renaming old commands or changing existing kinds.
- [x] Poison launcher/socket/transport hooks in tests; valid and invalid new CLI paths
  must never call them. Assert all autonomous/live/tactical flags remain false.
- [x] Document exact synthetic descriptor/manifest contracts, the command
  `.venv/Scripts/python -m psp_buddy inspect-map --config LOCAL_CONFIG --records LOCAL_MANIFEST`,
  representative versus alias distinctions, resource field limits, identity provenance,
  unsupported name/MV/coordinates/sides/actions and no live fallback. No game literals.
- [x] Run CLI tests plus old named/structural inspection tests; expected all pass.

## Task4: Private evidence verification, complete checks and review

Files: private scripts/profiles/data only under `local/representative-inspection-20261016`;
update this plan, research transition summary and map-evidence summary with results.

- [x] Build a private offline exporter from retained RAM/capture spans. Check overlapping
  bytes agree before canonicalizing disjoint windows; split at64KiB, enforce128/1MiB.
  No full-RAM fallback in public decoder/CLI, no emulator connection or new game input.
- [x] Export exact private profiles/anchors for retained69/12/26maps and six trial captures.
  Run actual inspect-map for each; compare counts, representative SETS, IDs/resources,
  selector index2 round trip, restored selected binding and DEF/MOB. Unsupported evidence
  must report a limitation; do not weaken contracts or fabricate expected observations.
- [x] Run `.venv/Scripts/python -m pytest -q`, `.venv/Scripts/python -m ruff check src tests`,
  `.venv/Scripts/python -m mypy src`, `.venv/Scripts/python -m pip wheel . --no-deps
  --no-build-isolation --wheel-dir local/representative-inspection-wheel`, and
  `.venv/Scripts/python -m psp_buddy --help`. Expected all pass; wheel remains private.
  Use a fresh ignored pytest basetemp with normal filesystem access if sandbox denies it.
- [x] Independently review `git diff HEAD`, intended untracked modules/tests/docs and
  acceptance evidence with requesting-code-review. Fix Critical/Important findings via
  observed failing regression tests; rerun affected checks and rereview. Report Minor.
- [x] Check `git diff --check`, `git status --short`, ignored private evidence and wheel
  contents. No game bytes, private profiles or local absolute paths in public fixtures.
  Record actual tests/counts/limitations and next programme dependency. No automatic commit.

Check five-hour usage at task boundaries; stop below10%remaining with handover. Do not
reopen/reconnect/reload the completed trial helper; PPSSPP remains user-owned and open.

## MVP scope clarification — 16 October 2026

The user explicitly confirmed that transformation actions are not needed in the MVP.
The completed transform trial is evidence for decoding the currently selected form/stat
record only. This approved offline reader adds no Transform action, planner choice,
executor recipe or runtime control. Do not schedule further transformation research as
an MVP acceptance requirement. Continue the representative reader solely to obtain one
correct current robot/pilot/stat binding per candidate object.

## Implementation verification checkpoint — 16 October 2026

Core, strict IO and CLI implemented; user's no-Transform MVP boundary preserved. New
production modules representative_inspection.py and representative_inspection_io.py;
new descriptor/manifest dispatch only. Old structural/named interfaces unchanged.

Observed RED->GREEN: missingcore/IO modules, newCLI dispatch/identity behavior, descriptor
hardlinks, node-storage arithmetic, packed adjacent records, exclusion signed32 semantics.
Actual retained-layout corrections: storage node capacities1024+1664=2688 with per-list
traversal bound1664; fullcaptured96/88byte windows can overlap unused tails, while interpreted
stat footprints36/62bytes must not conflict. Public fixtures remain synthetic.

Fullsuite864passed1skipped (Windowssymlink creation privilege unavailable); then two more
CLI safety tests added and fullnewCLIfile5passed. Ruff src/tests clean; strictmypy25source
files clean; local wheel built and inspected29files with no private assets. Actualoffline
CLI8cases original69,portable12,and sixformcaptures26 all match expected representatives
and resources; allcapabilityflagsfalse. Privateprofiles/spans/reports under ignored
local/representative-inspection-20261016; no new emulator read,input,save,reload or close.

Final independent code review pending. Do not mark finished until material findings fixed
and checks rerun as needed. Preserve userstageddocs/index and alluncommitted work.


## Completion and final review � 16 October 2026

Approved offline representative-reader extension complete. Independent review found no
Critical/Important findings; one stale README approval sentence was corrected. Fullsuite
864passed1skipped plus5focusedCLItests (including two added after fullsuite); Ruff and mypy
25sourcefiles, wheel and actualofflineCLIeightcases passed. OneWindows symlink test remains
skipped due missing creation privilege; regular/hardlink rejection cases pass. This is an
explicit verification limitation, not an implemented symlink bypass. No commits.

The completed trial remains open/idle and untouched throughout production implementation.
MVP Transform actions are excluded. New public modules/tests contain synthetic data only;
private profiles/rawspans/CLIreports and wheel are ignored under local. No tactical flags
were enabled. Future work should address remaining affiliation/action/terrain/legal-action
and authenticated tactical observation gaps under the existing whole-programme plan,
without repeating transform trials or adding a Transform executor.
