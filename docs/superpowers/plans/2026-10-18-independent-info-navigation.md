# Independent Info navigation implementation plan

**Goal:** Agent navigates to Destiny Info through timed MCP button requests and collects
the necessary built-in screenshots, without human-ready acknowledgements.

**Architecture:** New project-owned MCP stdio server uses a bounded trial mailbox. The
existing launch-bound helper handles requests through its one debugger adapter and a
whole-investigation lock. No second debugger connection, live hotpatch or upstream edit.
Screenshots continue through supported Computer Use > Debug > Take screenshot.

**Scope:** Cursor movement, opening a unit menu and selecting Info only. No unit Move,
Attack, Standby, End Turn, saves, cheats or automatic closure. No commits.

## Wire/API contract

Mailbox request: {trial_id,request_id,operation,arguments}. Operations press and verify.
arguments always contain sequence (1-based), screen_file (basename under current runtime
SCREENSHOT), screen_sha256 and context (map/unit_commands/info).
Press additionally contains button, duration (1..3frames; normally2), purpose
(cursor/open_unit_menu/menu_direction/open_info/cancel). open_unit_menu requires
cursor_tile equal trusted Destiny tile; open_info requires highlighted_entry:"Info".
Only up/down/left/right/circle/cross; confirm only the two explicit allowed purposes.
No raw-debugger events or other PSP buttons. At most16taps, strict sequence, no retry.
Screens must be regular unlinked JPEG/PNG, current-trial fresh, bounded, valid/nonblank,
hash-matching. No confirm using a screenshot acquired before the preceding button receipt.
Directional steps may share one fresh map/menu observation at most twice, then require
a new frame. Semantic context/entry labels are agent-observed interpretations, explicitly
not a calibrated machine screen classifier. Every action is grounded in an inspected image.

Service API InfoNavigation(session,adapter,target_tile,evidence_dir,verify_observer).
async execute(operation,arguments)->JSON-safe dict. verify_observer performs trusted
two-sample final selected-Info and unchanged-roster/resource/position validation, returns
scalar target identity/resources. Neither old human_ack schema nor old helper state is forged.

## Tasks (bounded delegated write scopes)

- [ ] TDD production src/psp_buddy/info_navigation.py and tests/unit/test_info_navigation.py.
  Observe meaningful failures for unsafe confirm, wrong/stale trial frame/hash, wrong
  cursor, exhausted budget, replay/sequence, lock deadline, transport errors, no capture
  before explicit need and final terminal result. Use synthetic issuer-created sessions.
- [ ] TDD src/psp_buddy/navigation_mailbox.py, tests/unit/test_navigation_mailbox.py,
  tools/ppsspp_navigation_mcp.mjs and tests/node/navigation_mcp.test.mjs.
  Reuse capture mailbox safety pattern without modifying capture files. Atomic bounded
  requests, replay rejection, one outstanding operation, strict schema and terminal
  failure. Tool names ppsspp_press_button and ppsspp_verify_info; result metadata only.
- [ ] TDD new private local/move-attack-trial-20261017/navigation_handoff.py and
  test_navigation_handoff.py. Static startup injection, shared whole-investigation lock,
  no requests before baseline readiness, queued timeout counts, same owned adapter.
  Baseline supplies target tile/identity. Final observer takes two stable coherent samples,
  verifies Destiny selected Info and unchanged full roster/resources/tiles, persists
  agent-navigation evidence separately. No fake human acknowledgements.
- [ ] Run focused tests and regressions, then full configured pytest suite, Node tests,
  Ruff whole/private, strict mypy, wheel and CLIhelp. Commands follow docs/usage.md;
  use unique ignored local/pytest-* basetemp. Offline checks never use PPSSPP.
- [ ] Independent review against approved spec; fix blocking findings, rerun affected checks.
- [ ] Activate after normal human closure, with fresh original SYSTEM backup and Launcher
  complete original/portable save/state/config SHA-256 protection. New empty evidence run.
  User approval already covers this bounded test; no repeated navigation-ready questions.
- [ ] Establish actual current cursor/menu by built-in image; calibrate one timed cursor
  step, then bounded route to target. Inspect command menu, highlight Info, confirm only
  after screenshot verifies that entry. Capture final Info and verify two memory samples.
  Stop on uncertainty, preserve open game, do not reconnect or escalate to battle commands.
- [ ] Record successful steps or precise stopped stage, snapshot/source preservation and
  resume point in progress/handover. Do not mark ready until live acceptance passes.
