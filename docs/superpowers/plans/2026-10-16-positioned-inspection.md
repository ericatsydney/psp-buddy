# Positioned representative inspection implementation plan

> Written design approved by the user on16October2026; no commits or emulator operations.

**Goal:** Join selected robot stats to validated zero-based tiles in an explicit offline report.
**Architecture:** A pure immutable wrapper reuses the representative decoder and adds
geometry validation, strict nested descriptor IO and a separate inspect-map dispatch.
**Tech stack:** Python dataclasses/hashlib/pathlib,pytest,Ruff,mypy,setuptools.

## Task1 — Core and strict parser (bounded worker)

Files create src/psp_buddy/positioned_inspection.py,positioned_inspection_io.py;
tests/unit/test_positioned_inspection.py,test_positioned_inspection_io.py.

- [x] Write failing import/behavior tests using existing synthetic representative sample.
  Define GeometryProfile(width_address,height_address,code_anchors,evidence_ids),
  PositionedInspectionProfile(representative_profile,geometry), and pure decoder as in spec.
  Use a synthetic geometry anchor and captured dimension bytes; write object+26/+28.
  Example positive assertion: report.to_dict()['representatives'][0]['tile_x']==3 and
  report.to_dict()['dimensions']=={'width':8,'height':7}. Observe red before code.
- [x] Implement immutable validation and composition. Read all geometry fields from one
  covering supplied span perwindow; no live helpers. Validate anchors before field decoding,
  full128spans/1MiB budget through base decoder. Use dataclasses.replace on the nested
  immutable profile with the deduplicated geometry/recipe anchor union (<=32entries/16KiB)
  so existing semantic-region checks cover every new fingerprint. Test new anchors inside
  pool/stat windows reject and caller profile remains unchanged.
- [x] Add red/green boundary tests widths0/1025/product1025, coordinatewidth/height/65535,
  legalwidth-1,height-1, missing dimensions/bytes, malformed profile and anchor/identity.
  Empty roster still requires dimensions. Source/form changes must preserve object tile.
- [x] Implement exact nested JSON parser; reject unknown/missing/duplicate/bool/nonfinite
  input through existing bounded helpers. Preserve original parsers and manifest contract.
- [x] Run focusedpytest,Ruff,mypy; root reviews before CLI integration.

## Task2 — CLI/docs (root after reviewed interface)

Files modify src/psp_buddy/cli.py,README.md,docs/usage.md;
create tests/unit/test_positioned_cli.py.

- [x] Observe failing real synthetic inspect-map success/identity-before-recordIO tests.
- [x] Add positioned kind branch, no-link descriptor guard, new parser and same bounded
  representative_spans loader. Use nested identity before binary reads; standard metadata.
- [x] Test exact tile/dimensions, falseflags, unavailablefields, invaliddata returns2/no
  partialstdout, socket/launcher hooks poisoned and subprocess no-live-import/no-file-write.
- [x] Document descriptor/manifest and zero-based captured-position caveat; no battle/MV/
  terrain/side claims. Keep old commands/profiles/output unchanged; run CLI regressions.

## Task3 — Private evidence, verification and review

Private files local/positioned-inspection-20261016 only. Public evidence notes/docs updated.

- [x] Export dimension/code windows and positions from retained original/portable RAM and
  six alreadycaptured trial samples. Verify overlaps agree before canonicalizing disjoint
  <=64KiBspans, total<=1MiB and count<=128. Profiles never shipped, no fullRAM livefallback.
- [x] Run actualCLI for69/12/26 maps, compare all107coordinate pairs with existing named
  geometry reports and six trial positionlists; verify Z(18,13),G00(17,4). No emulator IO.
- [x] Run .venv/Scripts/python -m pytest -q; -m ruff check src tests; -m mypy src;
  -m pip wheel . --no-deps --no-build-isolation --wheel-dir local/positioned-wheel;
  -m psp_buddy --help. Expected allpass; record legitimate skipped privilege tests.
- [x] Independent requesting-code-review against diffHEAD and intended untrackedfiles.
  Fix Critical/Important with failing regression tests, rerun checks and rereview.
- [x] git diff --check/status; verify privateignore/wheelcontents, leaveindex/PPSSPP untouched.
  Record actual outcomes and nextprogramme dependency; no commits or automaticnewtrial.

Check quota eachtask boundary; stop substantial work below10%remaining. Existing approved
representative work remains uncommitted; current open PPSSPP session must be preserved.

## Positioned reader implementation checkpoint — 16 October 2026

Core and strict wrapper parser implemented in positioned_inspection.py and
positioned_inspection_io.py; new CLI kind only, existing kinds unchanged. Synthetic
core/IO59tests plus5positionedCLI tests. Fullsuite930passed1existingWindowssymlinkskip;
Ruff src/tests,strictmypy27sourcefiles,wheel/help pass. No emulator operations or commits.

Private actualCLI eightcases reproduced69/12/26candidates with dimensions28x28,34x26,24x34,
matching all107distinct positions in prior named reports and all6trial observations.
Artifacts local/positioned-inspection-20261016, verifier local/verify-positioned-20261016.py.
Additional geometry bounds-code fragments were taken from retainedRAM and checked common
across clean original/portable and retained development code; supplied alongside trial
spans as explicit composite static-code evidence. They are not claimed atomic with new
trial captures or live authentication. Current trial positions still originate solely
from alreadycaptured object bytes. Source identity for original/portable uses their
existing named-report emulator identity; newcurrent captures use1.20.4.

Final independent review pending; retain all userstaged/unstaged work and open emulator.


## Completion

Independent final review found no Critical,Important or Minor code findings. All planned
positioned-reader work is complete with930passingtests,1pre-existing privilege-relatedskip,
cleanRuff/mypy27sourcefiles,wheel/help andeightactualofflineCLI evidencechecks. No live
capability enabled, no emulator operation and no commit. The programme still needs side,
action/terrain/legal-action and authenticatedlive tactical observation work. Do not repeat
completed form/position research or start another emulator session automatically.
