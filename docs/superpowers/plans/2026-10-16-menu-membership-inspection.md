# Offline menu-membership implementation plan

> Written design approved by the user on16October2026. No commits or emulator operations.

**Goal:** Join selected robot/stat/tile records to evidence-bound Ally/Foe menu membership.
**Architecture:** Immutable offline positioned-reader wrapper with strict nested profile,
protected expected mask-table fingerprint, direct object-byte filtering and explicit unknownside.
**Tech stack:** Python dataclasses/hashlib/struct,pytest,Ruff,mypy,setuptools.

## Task1 — Pure decoder (bounded core worker)

Create src/psp_buddy/menu_membership_inspection.py and
tests/unit/test_menu_membership_inspection.py. Read approved spec, positioned/representative
APIs and synthetic positioned_sample. Do not edit existing core modules.

- [x] Write failing import/positive test; create synthetic fouru32masktable and groupbyte.
  Example behavior: report.to_dict()['representatives'][0]['menu_membership']=='ally_menu'
  while report.to_dict()['unavailable_fields']['side'] remains present and allflagsfalse.
- [x] Implement frozen profile/report, pure decoder and readonly-table fingerprint computed
  from declared expected masks. Combine via private dataclasses.replace nested profiles;
  validate full combined recipe/geometry/new/table fingerprint count and bytes before decode.
- [x] Meaningful red/green tests for exactlyfourvalid masks,disjointfullcoverage,0..3distinct
  indices,table mismatch,group0/15 vs16/31/32/255,missingbytes,overlap/budgets,empty/multiple
  objects, deterministic counts/order, supported outsidecategory without neutral inference.
- [x] Test table/newfingerprint in pool/stat/dimension regions rejects; shared exact anchors
  allowed, partial overlaps rejected. Caller profiles remain immutable. Run focusedpytest,
  Ruff and strictmypy; root reviews before dependencies.

## Task2 — Parser/CLI (IO worker after core interface)

Create menu_membership_inspection_io.py and tests/unit/test_menu_membership_inspection_io.py;
modify cli.py and create tests/unit/test_menu_membership_cli.py. Preserve existing branches.

- [x] Write failing exact JSON/nesteddescriptor and realCLI success/identity-before-recordIO
  tests, observe red; implement parser and newkinddispatch with no-linkdescriptor guard.
- [x] Test unknown/missing/duplicate/nonfinite/bool/bounds/malformedtable data. Reuse unchanged
  representative_spans loader. Existing profile kinds retain strict schemas/output.
- [x] Poison livehooks,subprocess assert no controllerimports/no filewrites. Badgroup/table
  returns2/no partialstdout. Verify labels/counts/unknownside/falseflags; run regressions,
  Ruff and mypy before root integration.

## Task3 — Private evidence/docs/checks/review (root)

Private files only local/menu-membership-inspection-20261016. Public README.md/docs/usage.md
and research/evidence summary updates must distinguish menu membership from allegiance.

- [x] Export expected static table/query/producer fingerprints from verified retained RAM;
  combine private spans with explicit composite-provenance notes, no new live read/trial.
- [x] Run actualCLI on sixcurrentcaptures20/5/1 and rawregressionmaps24/25/20/0,8/4/0/0.
  Confirm allrows joined by object, stats/positions intact and WingZero outsidebothmenus.
  Do not claim new crossstage UIlabel validation from counts alone.
- [x] Run .venv/Scripts/python -m pytest -q; -m ruff check src tests; -m mypy src;
  -m pip wheel . --no-deps --no-build-isolation --wheel-dir local/menu-membership-wheel;
  -m psp_buddy --help. Expected allpass; document Windows privilege skips.
- [x] Independent requesting-code-review of diffHEAD plus intendeduntracked files/evidence.
  Fix Critical/Important through redregressions; rerun checks and rereview. Report Minor.
- [x] git diff --check/status, privateignore/wheelcontents, preserveindex/PPSSPP and record
  results/limits/nextprogramme dependency. Leave everything uncommitted.

Check allowance eachtaskboundary and stop substantial work below10%remaining. No sideenum,
Transform action, tacticalSnapshot or battle capability is authorized by this design.


## Completion � 16 October 2026

User explicitly approved the written design. New immutable core and strict parser,
CLI dispatch and user documentation implemented; old profiles/output remain unchanged.
Observed behavioral RED->GREEN for missingmodules/newCLI dispatch and identity-beforeIO;
74newcore/parser tests plus6CLI tests pass. Fullsuite1010passed1existingWindowssymlinkskip
(privilege unavailable). Ruff src/tests and strictmypy29sourcefiles pass; wheel/help and
whitespace checks pass. Wheel33files inspected; private profiles/rawspans/reports excluded.
Initial pytest/pip attempts in sandbox hit temporary-directory permissions; equivalent
normal-access runs passed. No code fix was inferred from environment failures.

ActualofflineCLI eightcases passed: six currentcaptures categorycounts20/5/1/0 and
WingZero outsidebothmenus; other rawregressions original24/25/20/0 andportable8/4/0/0.
Every previous selectedrow field, stat and tile is unchanged. Staticquery/producer/table
fragments supplied from matching cleanretainedRAM are explicit compositeprovenance, not
a new live/atomiccapture claim. Private verifier local/verify-menu-membership-20261016.py;
artifacts local/menu-membership-inspection-20261016. Labelsource remains user supplied,
tacticalside and thirdparty hostility unknown, allcapabilityflagsfalse.

Independent final review found no Critical,Important or Minor findings. No emulator
operations, originaldata writes, reconnect, save/load, closure, commits or publishing.
Next programme dependency: action availability and its actual UI/phase semantics, then
legal-movement/terrain/combat evidence and authenticated tactical integration. Do not
repeat completed form/position/menu membership research or add Transform actions.
