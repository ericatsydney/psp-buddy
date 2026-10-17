# Offline End Phase inspection implementation plan

Approved design: ../specs/2026-10-17-end-phase-inspection-design.md. User approved in chat.
Goal: report two-bit counters and verified UI aggregate offline. Python frozen dataclasses,
strict JSON and existing menu/representative validators; no emulator or live capabilities.
Use bounded delegated tasks, observed failing tests, review before dependent integration.
No commits; preserve existing staged and unstaged work.

- [x] Core: create src/psp_buddy/end_phase_inspection.py and
  tests/unit/test_end_phase_inspection.py. Reuse menu_sample synthetic capture. First test
  counter values0/1/2/3 and group0/3/12; expected scope only0, counter2 contributes1.
  Run python -m pytest tests/unit/test_end_phase_inspection.py -q: fail missing module.
  Implement frozen profile composition and pure decoder. Rely on nested source/cache
  exclusion filtering to reject enabled matching pairs before counters; explicitly verify
  this invariant in tests. Test profile budgets/mutation, unknown fields and null objects.
  Test empty and100+ cases for raw count versus modulo display using validated fixtures.
- [x] IO: create src/psp_buddy/end_phase_inspection_io.py and
  tests/unit/test_end_phase_inspection_io.py. First parser test fails missing module.
  Exact keys and nested menu descriptor, schema1, anchors and evidence validation; reject
  bool/schema/unknown keys and preserve old parser. Run focused parser tests after core.
- [x] CLI: modify src/psp_buddy/cli.py; create tests/unit/test_end_phase_cli.py. First run
  real offline descriptor must fail unsupported kind. Then add dispatch with nested identity
  check before manifest loading; reuse representative_spans loader. Tests success, mismatch,
  unsupported group, missing bytes, no partial stdout and all false capability flags.
- [x] Private regression: wrap retained menu profiles with explicit count/resolver/UI anchors,
  retain composite provenance; actual CLI scope/count original24/13,portable8/5,current20/20.
  Preserve old row fields. No game bytes or profiles tracked.
- [x] Verification: .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp local/pytest-UNIQUE; python -m ruff check src tests;
  python -m mypy src/psp_buddy; python -m pip wheel . --no-deps --no-build-isolation
  --wheel-dir local/wheels; python -m psp_buddy --help; git diff --check.
  Expected all pass except existing unavailable Windows symlink privilege skip.
- [x] Review: inspect git diff HEAD and intended untracked modules/tests; independent reviewer
  checks approved design, resolver behavior, anchor overlap/budget and no live capability.
  Fix Important/Critical findings, rerun affected checks. Update README.md,docs/usage.md,
  research summary and parent handover; mark this plan with exact results and limitations.

## Verification record

Core32,parser32,CLI4 newtests observed meaningful RED then GREEN. Final fullsuite1078passed,
1existingWindowssymlinkprivilege skip. Ruff src/tests passes; strictmypy31sourcefiles passes;
wheel/help and diff checks pass. Initialfullrun useddefaulttempoutsideworkspace and8existing
launcher tests correctlyrejected runtimepath; rerunwithdocumenteduniquelocalbasetemppassed.
No launcherbehaviorchanged. Preliminaryreview found inheritedpoolanchors missing fromglobal
budget; regressionfailedbeforefix, combineddeduplicatedpool/recipe/menu/table/geometry/end
budgetnowenforces32entries/16KiB. Valid100/101actorfixtures testdisplay0/1andcounter2counts1.
PrivateactualCLIeightcases reproduce24/13,8/5,and20/20sixtimes withalloldrowfieldsunchanged.
Staticcode/text spans areexplicitcompositeprovenance,notnewlive/atomiccapture.
Private verifier:local/verify-end-phase-20261017.py; results:local/end-phase-inspection-20261017.
No emulator operations,savechanges,commits,pushes or publishing. Final independent review cleared: no remaining Critical, Important or Minor findings.
