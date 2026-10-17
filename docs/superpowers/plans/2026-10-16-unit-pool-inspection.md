# Bounded unit-pool inspection Implementation Plan

> **For agentic workers:** Execute bounded tasks through subagents with review between dependencies. Available skills are writing-plans, test-driven-development and requesting-code-review; no unavailable skill is required. User instructions prohibit commits.

**Goal:** Enumerate structural candidate slots and all actor aliases from supplied bounded spans.

**Architecture:** A pure immutable decoder validates the approved fixed layout, identity and code fingerprints. Strict offline IO feeds the decoder through existing inspect-map dispatch; named-record behavior stays unchanged.

**Tech Stack:** Python3.11+, dataclasses, hashlib, pytest, Ruff, strict mypy, setuptools.

Approved design: docs/superpowers/specs/2026-10-16-unit-pool-inspection-design.md (user approved16October2026). Preserve pre-existing staged docs. No emulator trial or live reads are required.

## Task1: Pure decoder (core worker)

Files: create src/psp_buddy/unit_pool_inspection.py and tests/unit/test_unit_pool_inspection.py.

- [x] Write synthetic fixtures with pool at0x08801000, owner at0x08802000, actor data at0x08803000, anchor at0x08804000. Use capacity3, stride104, actor capacity4, stride16; slot1 has references2 and state0x401, rows point to two distinct mech/pilot descriptors. Fill owner offsets8/12/16/20. Include no game bytes.
- [x] Observe import failure with `.venv/Scripts/python -m pytest tests/unit/test_unit_pool_inspection.py -q` before implementation.
- [x] Implement frozen UnitPoolInspectionProfile, InspectionSpan, UnitPoolInspectionReport, UnitPoolSlot, UnitPoolActorBinding, and a frozen CodeAnchor(address,size,sha256) helper. Profile constructor fields exactly mirror descriptor except kind/schema_version. Expose decode_unit_pool_inspection(profile, spans, game_id, patch_id, emulator_version). Report exposes to_dict() with exact approved JSON keys. No IO imports.
- [x] Build meaningful assertions:

```python
report = decode_unit_pool_inspection(profile, spans, 'g', 'p', 'e').to_dict()
assert report['candidate_count'] == 1
assert report['autonomous_execution_enabled'] is False
assert report['roster_completeness'] == 'candidate_slots_only'
```

- [x] Test every approved identity/type/bounds/alignment and anchor limit, span overlap/gap/size, owner equality and pointer window, three excluded states and accounting, valid empty pool, aliases preserved and sorted, distinct ambiguity sets, included null descriptors, excluded null descriptors allowed, unknown object pointer rejection and exact serialization keys.
- [x] Implement only after red; run focused tests after each logical group. All malformed inputs raise ValueError, never tactical partial reports. Include pure API validation, not merely parser validation.
- [x] Run `.venv/Scripts/python -m ruff check src/psp_buddy/unit_pool_inspection.py tests/unit/test_unit_pool_inspection.py` and `.venv/Scripts/python -m mypy src/psp_buddy/unit_pool_inspection.py`. Expected clean. Root reviews core before integration.

## Task2: Strict IO and command dispatch (IO worker, disjoint files)

Files: create src/psp_buddy/unit_pool_inspection_io.py, tests/unit/test_unit_pool_inspection_io.py, tests/unit/test_unit_pool_cli.py; modify src/psp_buddy/cli.py. Read existing inspection_io.py/map_inspection_io.py/test_cli.py conventions.

- [x] Write failing strict-schema and command tests before production changes. Run `.venv/Scripts/python -m pytest tests/unit/test_unit_pool_inspection_io.py tests/unit/test_unit_pool_cli.py -q`; expected missing module/unsupported descriptor failure.
- [x] Implement parse_unit_pool_inspection_profile(values) returning the core profile, and load_inspection_spans(path) returning tuple[InspectionSpan,...]. Exact descriptor keys, limits and binary field contracts are in approved spec; reuse bounded JSON/file helpers. Validate at most32files/64KiB each/1MiB total before retaining samples. Resolve relative paths to manifest. Enforce nonempty no-NUL paths, exact keys/kind/version, duplicate-key and nonfinite rejection through existing JSON loader.
- [x] Dispatch descriptor kind before calling either strict parser. For unit_pool_inspection, compare config identity before reading spans, decode and serialize through to_dict(). Add command/configuration metadata without overwriting fixed capability/provenance fields. Keep map_inspection branch behavior unchanged.
- [x] Test wrong manifest kinds in both directions, unknown/missing keys, booleans, bad evidence and hashes, changed/oversized/missing/nonregular files, source identity mismatch before binary IO, exact false capability booleans and all unavailable fields. Poison live transport opening to prove no fallback.
- [x] Run focused tests and named-map CLI regression tests. Expected all pass. Worker waits for core interface rather than editing core.

## Task3: User documentation and integrated review (root)

Files: README.md; docs/usage.md; docs/superpowers/plans/2026-10-16-unit-pool-inspection.md; existing map plan append only.

- [x] Document descriptor/manifest contracts with synthetic values and offline inspect-map invocation, current limitations and unavailable tactical fields. Explain that supplied anchors do not authenticate live identity or coherent timing. Do not ship literal game profiles or retained RAM.
- [x] Review both workers' diffs against every acceptance criterion and include intended untracked files.
- [x] Run `.venv/Scripts/python -m pytest -q`, `.venv/Scripts/python -m ruff check .`, `.venv/Scripts/python -m mypy src`, `.venv/Scripts/python -m pip wheel . --no-deps --no-build-isolation --wheel-dir local/unit-pool-wheel`. Expected all pass, wheel built locally. Run `.venv/Scripts/python -m psp_buddy --help` and actual synthetic inspect-map CLI flow through tests.
- [x] Use requesting-code-review skill for independent full working-tree review after checks. Critical/Important findings block completion; reproduce fixes with meaningful tests and rerun affected checks/review.
- [x] Run git diff --check and git status --short. Preserve index, saves and uncommitted user work. Record red/green results, full checks, review and remaining overall programme tasks. Check quota at task boundaries and stop substantial work below10% remaining.

No commits, pushes, emulator launch/control or automatic live/tactical enablement. Approval of this extension is recorded; no further confirmation is needed for its implementation.


## Completion checkpoint,16October2026

All three tasks completed. Core observed red before production and55 focused tests green.
IO/CLI observed missing-module red before production;49new tests plus existing regressions
pass. Full verification:707passed in46.08s, Ruff clean, strict mypy23source files clean,
wheel built. Exact docs JSON ran through the real CLI with1candidate/2aliases. Private
production reader comparison reproduced all three retained maps and every alias using
40040supplied bytes each. Final independent code review: no findings. Reviewer's additional
fixture tests encountered sandbox permissions; root required checks all passed.

Windows default pytest/pip temporary directories failed with PermissionError; corrected
commands used approved temporary-directory access. Actual successful full-suite command:
`.venv/Scripts/python -m pytest -q --basetemp=local/unit-pool-full-20261016a -p no:cacheprovider`.
Ruff/mypy commands are unchanged. Wheel command above succeeded with temporary access.
The final help-string clarification was linted/typed after full suite; it changes descriptive
text only. No further behavior changes followed passing tests.

Existing staged documentation remains staged; new feature files and docs are uncommitted.
Next overall programme dependency is evidence for current form/primary crew and remaining
map/tactical fields, then separately reviewed integration. Offline current-form investigation
can continue without touching emulator state. This completes this extension, not battle MVP.
