# Trial file retention — plan

Spec: `docs/superpowers/specs/2026-11-07-trial-retention-design.md`.

1. Tests first: `tests/unit/test_retention.py` (keep 5, protect, unrelated names, no marker,
   links, only `working`, error recorded). Run and see them fail (module missing).
2. Add `src/psp_buddy/retention.py` with `PruneResult`, `prune_runtime_archives`,
   `prune_working_copies`.
3. Test in `tests/unit/test_launch.py`: seven prior archives and working copies -> 5 left after
   `prepare`. See it fail, then call both functions at the end of `Launcher.prepare` and keep the
   result on `Launcher.last_prune`.
4. Verify:
   - `.venv/Scripts/python.exe -m pytest tests --basetemp local/pytest-ret -q` (all pass)
   - `.venv/Scripts/python.exe -m ruff check src tests`
   - `.venv/Scripts/python.exe -m mypy src`
5. Review `git diff HEAD`; note it in `docs/progress.md`.
