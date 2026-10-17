# Move/Attack MVP implementation plan

Approved spec: ../specs/2026-10-17-move-attack-mvp-design.md. Python existing planner and
executor interfaces; preserve models/historical fields, no emulator or commits.

- [x] Planner task: tests/unit/test_planner.py first RED for unknown healing fields and
  supplied Repair/Trust alongside valid attack/retreat; replace obsolete heal expectations
  with exclusion regressions and fresh post-move planning. Run .venv/Scripts/python.exe -m
  pytest tests/unit/test_planner.py -q. Then remove healing branch in src/psp_buddy/planner.py;
  preserve injured retreat, targeting/resources and stale/unknown legality handover. GREEN.
- [x] Executor task: tests/unit/test_executor.py first RED valid legal+recipe Repair/Trust
  requests must raise excluded_mvp_action with no sends; preserve cleanup. Remove support
  actions from success matrix, retain negative coverage. Add pre-observation execution guard
  in src/psp_buddy/executor.py; focused pytest GREEN.
- [x] Integration: update any synthetic supervisor scenarios expecting healing; preserve
  Wait/EndTurn/reactions as existing orchestration controls. No activation of live run.
- [x] Verify .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp local/pytest-UNIQUE;
  Ruff src/tests, strict mypy src/psp_buddy, wheel/help, git diff --check. All pass except
  existing Windows symlink privilege skip. No real emulator trial.
- [x] Independent review final diff HEAD and intended untracked files against spec, fix
  Critical/Important issues, rerun affected checks. Update README/usage and handover.

Disjoint delegated scopes: planner+planner tests; executor+executor tests. Root integration,
docs and verification. No unrelated edits, original index/staged documentation preserved.

## Results

Planner observed4failingregressions before removing healing branch;27planner tests pass.
Executor observed2validrecipe cases fail before adding excluded_mvp_action guard;52executor
tests pass. Guard precedes observation/provider/send while shielded release cleanup remains.
Fullsuite1078passed,1existingWindowsprivilegeskip usinguniqueworkspacebasetemp.
Ruffsrc/tests andstrictmypy31sourcefiles pass;wheel/help/diffchecks pass. Existing synthetic
supervisor/battle scenario needsnohealingedit andpasses. Publicmodel/APIfields retained;
legacy healing instructions cannotenableexcludedcommands. No emulatoroperationsorcommits.
Final independent review cleared: no Critical, Important or Minor findings. Next: writtenprotectedMove/Attackobservation
trialforcausalcounterconsumptionandpost-movecommandlegality; do notauto-launch/reload.
