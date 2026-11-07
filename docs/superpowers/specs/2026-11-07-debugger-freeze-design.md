# Debugger freeze after a press: reproduce, then recover — design

Date: 7 Nov 2026. Status: approved 7 Nov ("Reproduce, then fix"); Part 3 revised to the fallback the user chose.

## Problem

Four live runs stopped with `driver_error: ERR Protected navigation failed`:

| Run | Date | Last input before the freeze | Screen |
|---|---|---|---|
| fr-s33b | 1 Nov | two Down presses | weapon list |
| s2 | 5 Nov | Circle | (not recorded) |
| s2t6 | 5 Nov | Circle | (not recorded) |
| s2d | 6 Nov | three Down presses | Big O weapon list (ULJS00460_00050) |

In each, the next memory read waited the full adapter timeout (60 s), raised `TimeoutError`, and the
helper wrote `disabled.json` (`reads_disabled: true`) and stopped. In s2d even the adapter clean-up
(`adapter-cleanup-error.json`, 5 s limit) timed out, so PPSSPP's debugger WebSocket answered nothing for 65+ s,
while the game itself kept running (no crash in the Application log; the user could move the cursor
after the helper exited). The 0.2 s press gap (1 Nov, `DebuggerAdapter.PRESS_GAP_SECONDS`) made the
freeze rarer but did not remove it.

Unknowns: which debugger request is the one left unanswered (`cpu.stepping`, the `cpu.status` poll,
`memory.read`, `cpu.resume`); whether the link comes back by itself after > 60 s; whether a fresh
WebSocket connection is accepted while the old one is frozen; whether a window message to PPSSPP
(no game input) un-sticks it. The `act_read` log line also says `"outcome": "ok"` for the hang,
because `_act_read` does not catch `TimeoutError`.

A second, smaller block: a `cursor_budget` handover reports `screen_state: map` but can leave a story
dialogue on screen (s4-d, 4 Nov), because `turn_next` hands over without `settle_dialogue`.

Out of scope (user, 7 Nov): ally safety. When an ally dies the runner hands over, as today.

## Reuse check

No existing tool covers this: it is a PPSSPP 1.20.4 debugger behaviour under our own adapter. The
PPSSPP WebSocket API docs list no keep-alive or recovery request. We reuse the existing adapter,
launch session, helper, backups and `run.py`; the probe reuses `restart.ps1` and the act IO.

## Approach (chosen: A)

- **A. Reproduce, then fix (chosen).** Log every debugger request; a protected stress probe reproduces
  the freeze and tries the recoveries in order; build in only the recovery that worked.
- B. Blind recovery: reconnect + retry without a probe. Rejected: the reconnect may hang too, and we
  would learn that only in a real run.
- C. Mitigate only: longer gap and a clean handover. Rejected as the fix: runs would still stop.

## Part 1 — request log (offline, TDD)

- `DebuggerAdapter` gets an optional `trace` callback. `_exchange` calls it once per request with
  `{"event", "ticket", "sent_ns", "seconds", "outcome": "ok" | "timeout" | "error: <type>"}`, also
  for `cpu.stepping` / `cpu.resume` (sent) and each `cpu.status` poll in `_transition`.
- The helper writes the trace to `debugger-trace.jsonl` in the evidence dir (append, bounded to the
  last 5000 lines by rotation to `debugger-trace.1.jsonl`).
- `_act_read` logs `"outcome": "timeout"` (or the exception type) for any exception, not `ok`.
- Failure behaviour: a trace write error never fails a request (counted, reported in the handover).

## Part 2 — stress probe (live, protected)

`local/m17-tools/freeze_probe.py <checkpoint> --label L --cycles N` (default 400):

1. Launch exactly like `run.py` (WMI-detached `restart.ps1`, verified backups, quiet machine), plus the
   portable memstick backup.
2. On the map, open the anchor ally's Attack weapon list (path from the existing act IO; screenshot at
   each new screen). Each cycle: press Down or Up (alternating, stays inside the list), then
   immediately one small read (`menu_row`) — the pattern that froze (fp4 added a full state read every
   5th cycle; the map-cursor case was dropped: runs make hundreds of cursor reads without freezing).
   The unit is named by the driver (`--unit`) and the open list is checked on a screenshot before the
   cycles start. No Circle on a target, no Start: nothing in the game changes.
3. A read that takes > 10 s marks a freeze. The probe then tries, in order, logging each result:
   (a) keep waiting on the same socket up to 120 s more; (b) a harmless window message to PPSSPP
   (`WM_NULL` via `SendMessageTimeout`, no keys); (c) a second WebSocket connection (needs a probe-only
   bypass of `claim_connection`'s one-claim rule, bound to the same PID and loopback); then reads
   `cpu.status`, and resumes the CPU if it was left stepping.
4. Ends with Cross back to the map, a graceful PPSSPP close, and an originals check (0 changed).
   Writes `freeze-probe-report.json`: cycles run, freezes, the request that hung, and which recovery worked.

Success: at least one freeze reproduced with its hung request named, or 400+ cycles with none (then
the gap is raised and the probe repeated once). Limit: 2 probe runs before reporting back to the user.

## Part 3 — fallback recovery in the runner (offline TDD)

Revised 7 Nov after Part 2: the probe did not reproduce the freeze (fp3: 400 cycles / 799 presses;
fp4: ~9600 requests, stopped by the user), so no recovery was proven. The user chose the fallback
("wait-and-retry, then a clean handover"):

- **Freeze timeout:** every `InfoNavigation` reader (`READERS`) is wrapped by `_guarded` with a
  15 s limit (`READ_FREEZE_SECONDS`; normal reads < 1 s, state reads ~2 s).
- **Recovery (reads only):** on a freeze, `DebuggerAdapter.recover()` runs only if the request that
  set `uncertain` was a read, status, pause or resume (`RECOVERABLE_EVENTS`), no button is held and no
  pause is owned. It asks `cpu.status` (2 x 10 s); if answered, it clears `uncertain` and resumes a CPU
  our abandoned pause left stepping (a user pause stays), also bounded by 10 s. Then the read runs once
  more. Late replies with an old ticket are ignored by ticket matching.
- **Clean handover:** an unrecovered read, a second freeze, or a press timeout raises `DebuggerFrozen`
  (not an `ActIOError`, so the act code sends no retreat presses). `execute` turns it, or a
  `TimeoutError` that left the adapter uncertain, into reason `debugger_frozen`: `handover.json` with
  `screen_state: unknown` and the `freezes` list; every later operation answers the same handover
  without reads or input. `clear_loop`, `run.py` and `backout.py` report `debugger_frozen`.
- **Records:** each freeze is logged (`debugger_freeze` in agent-navigation-inputs.jsonl) and listed in
  `handover.json` (`freezes`); not in the turn report.
- **Limits:** the helper's operation limit is now 120 s for every operation but a raw press
  (was 60 s for state/turn_next), so a 15 s freeze + <= 30 s recovery + 15 s retry fits. A freeze late in
  an act (ACT_SECONDS 105) can still overrun 120 s and disable the helper, as before.
- Safety rules kept: a press whose outcome is uncertain is never repeated; no reconnects.

## Part 4 — dialogue before a cursor-budget handover (offline TDD)

In `turn_next`, when the reason is `cursor_budget` and `_dialogue_pending` is set, run
`act_macro.settle_dialogue` first; if it does not settle, the handover reason stays `cursor_budget`
and `handover.json` records `dialogue_pending: true` (never `screen_state: map` with a dialogue up).

## Acceptance criteria

1. Unit tests: trace record per request (ok / timeout / error), status polls traced, trace write failure
   harmless; `_act_read` logs a failed read's outcome; adapter `recover()` (read timeout recovered and
   CPU resumed, silent status, press never recovered, user pause kept, bounded resume); recovery path
   (read freeze -> recovery -> re-read succeeds; recovery fails -> `DebuggerFrozen`; press freeze -> no
   repeat; frozen turn_next -> `debugger_frozen` handover and no further reads); driver, run.py and
   backout.py name `debugger_frozen`; dialogue settle before `cursor_budget`.
2. Full checks pass: `pytest`, local tool tests, `ruff`, strict `mypy`.
3. Probe report names the hung request (or shows none in 400+ cycles) and the recovery result; backups
   verified, originals 0 changed. Result: none in 400 cycles (fp3) or ~9600 requests (fp4).
4. Live slot-2 run with the fix: no `driver_error`; any freeze is either recovered (counted) or a clean
   `debugger_frozen` handover with the game on the map or a named screen.
