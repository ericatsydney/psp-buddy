# Fewer cursor moves — implementation plan

Spec: `docs/superpowers/specs/2026-11-01-fewer-cursor-moves-design.md`. Nothing is committed.
Verification commands as in `docs/superpowers/plans/2026-11-01-faster-reads.md`.

1. Tests first in `tests/unit/test_spirit_cast.py` (Spirited sim reports `screen` with `screens=True`):
   memory proof, walk fallback, per-run skip. Seen red (2 of 3; the fallback test documents today's
   behaviour).
2. `spirit_cast.py`: `skip_mechs`, `_map_in_memory`, `_back_to_map(memory_first=...)`.
   `plan_act.py`: `spirit_skip` through `plan_and_act` / `_plan_and_act` / `_cast`; no Spirit press
   reserve for a skipped mech. `info_navigation.py`: `_spirit_skip` per run.
3. Full verification list.
4. Live stage-33 run (`run.py m15-s33`), compare cursor presses (`goto_presses_used`) and outcomes with
   fs-s33a. After the user's animation change: prepare a new checkpoint from the re-saved slot and run.
