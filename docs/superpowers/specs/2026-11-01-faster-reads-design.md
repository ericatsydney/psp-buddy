# Faster reads: periodic process identity check — design

Status: approved by the user, 1 Nov 2026. Part of M15 speed-ups before P6 (other saves).

## Problem

In the stage-33 run m15s33b, 50 min of play contained 1,029 memory reads at about 1.0-1.4 s each (~23 min)
and ~520 logged presses. The memory reads themselves are small; the cost is
`LaunchSession.assert_bound()` (`src/psp_buddy/launch.py`), which every `cpu.stepping`, `cpu.resume`,
button press and capture runs. Each call starts `powershell.exe` with `Get-CimInstance Win32_Process` to
re-check the emulator's executable path, command line and creation date: 0.85 s measured on 1 Nov (cold);
a read pays it twice (pause + resume), a press once. Roughly 2,500 calls per run, ~20 min.

## Reuse check

- `psutil` would give the identity in-process, but it is not a dependency (pyproject: websockets, Pillow).
- A ctypes Win32 query (approach B) keeps a full check per call but needs fiddly command-line reading.
- Fewer/lighter reads (approach C) keeps the cost per pause and changes turn logic.
- Chosen (user, 1 Nov): approach A, cheap check every call + full check at most every 30 s.

## Design

`LaunchSession.assert_bound()`:

1. Always (instant): session not closed; `self._process.poll() is None` (the Popen handle we hold —
   while it is open Windows cannot reuse the PID, and a running process's image and command line cannot
   change); `_safe_path(self.memstick_root)`; no `installed.txt` beside the executable.
2. Full identity (`inspector.process(pid)` compared with the launch identity, executable and command line)
   only when `FULL_CHECK_SECONDS = 30` have passed since the last successful full check.
3. Forced full identity check: in `__init__` (as today), `claim_connection()` and `close()`.
4. The clock is injectable (`clock=time.monotonic`) for tests.

Failure behaviour is unchanged: any failed check raises `ValueError`; the adapter marks the transport
uncertain and the helper disables itself; `close()` refuses to terminate a process whose identity changed.

Not changed: debugger adapter, helper, act logic, press budget, backups, listener check, capture paths
(they call the same `assert_bound` and get faster too).

### Addendum after live run fr-s33a (1 Nov)

fr-s33a ran in 27 min (m15s33b: 57 min) with reads at median 0.01 s, but fired 24 attacks instead of 32:
seven `target_not_hittable` stops. The first hover hit read now comes before the game updates the hover
for the new cursor tile, and `no_target` was treated as final; the old ~1 s read had hidden that delay.
Fixes inside this scope, both test-first:
- `act._hit_when_ready` polls `no_target` like `unknown` (HIT_POLLS 5 × 0.6 s); a real `no_target`
  still stops, about 3 s later.
- `act.range_when_drawn` (used by `act.move` and `plan_act._open_move_range`) re-reads the state up to
  6 × 0.3 s until the move range is centred on the unit (same timing pattern; no failure seen live yet).

### Addendum after live run fr-s33b (1 Nov, user: "Yes, add gap")

fr-s33b stopped after ~14 min: PPSSPP's debugger did not answer a read for 60 s, right after two Down
presses. Hypothesis (unproven): pauses now follow presses and resumes within milliseconds. Fix:
`DebuggerAdapter` waits before taking a new pause until 0.2 s after the last press and 0.1 s after the
last resume (`PRESS_GAP_SECONDS`, `RESUME_GAP_SECONDS`). If a stall recurs, investigate PPSSPP's stepping
before any further change.

## Acceptance criteria

1. Unit tests (`tests/unit/test_launch.py`):
   - a second `assert_bound()` within 30 s does not call `inspector.process`;
   - after 30 s it does, and a changed identity then fails;
   - an exited process fails at once without calling the inspector;
   - `installed.txt` appearing fails at once;
   - `claim_connection()` and `close()` always run the full check (existing PID-reuse test still passes).
2. All verification commands pass (pytest, ruff, mypy, node, helper tests, m13/m15 tool tests).
3. Live: `run.py` on `local/checkpoints/m15-s33` (fresh verified backups by restart.ps1, CPU < 35%,
   detached WMI launch). Median `act_read` seconds < 0.4 (was ~1.0) and play behaves as in m15s33b
   (back-out to map, attacks fire, clean handover or clear). Turn-5 player-phase time is recorded for
   comparison (m15s33b: ~21 min).

## Exclusions

Lighter or fewer reads, battle animations off, skipping the repeated map proof, trimming sleeps and
emulator speed-up are separate follow-ups.
