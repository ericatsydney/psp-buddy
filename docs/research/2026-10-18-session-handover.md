# Session continuation — 18 October 2026

Continuing the approved human Destiny Move-one-tile-down/Standby diagnostic from
[17 October](2026-10-17-session-handover.md). No production changes or commits.
The only initial Git changes were this conversation's reporting/workflow notes.

The prior destiny-run-20261017T2100096872 did not reach ready: its initial baseline
saved capture-001-1.json, then the debugger closed with WebSocket code1001 while
sending during the next observation. disabled/startup-error/fatal-error records
are retained. This proves a connection close, not its cause. No request was replayed
and no completed Destiny action observation was claimed.

Current inventory before fresh launch found no PPSSPP or Python process; supported
Computer Use window inventory also found no PPSSPP window. Original SYSTEM was
copied and SHA-256 verified under
backups/destiny-original-config-20261017T234352Z-1e211f23b6f846deb740e838ee5921e3.

A new reviewed standby_handoff.py process started with -X utf8, hidden helper window,
fresh evidence directory and the existing protected Launcher. It enforces complete
original/portable save/state snapshots and portable configuration backups before launch.
Active pointer: local/move-attack-trial-20261017/active-destiny-run.json.
Run: local/move-attack-trial-20261017/destiny-run-20261018T0943512761.
Initial helper PID3704 is historical; verify before use.

Preparation completed at09:47 Brisbane: fresh four-directory/configuration snapshots
verified, PPSSPP PID13808 launched, two stable baseline observations accepted and
ready.json written. Known G00 baseline HP5000/EN121/SP55 passed; no disabled/fatal
record or stderr. Supported window inventory confirms the owned PPSSPP window.
The helper is idle, awaiting sequence2 unit-baseline. Preserve every snapshot and prior run.
Do not reconnect/replay a failed helper. The approved helper collects observations
only; all Destiny navigation/Move/Standby remains human-controlled. No automatic
inputs, cheats, combat, End Turn, save/load, or automatic emulator closure.

Next stages once ready: fresh Destiny Info binding, actual unconfirmed down-one
Move preview, confirmed post-Move, confirmed post-Standby. Fresh human readiness
is required at each stage; previous acknowledgements cannot be reused.

## Demand-driven MCP capture check

User requested investigation automation with screenshots only when necessary. Read-only
configuration/tool inventory confirms PPSSPP MCP is disabled, screenshot not allowlisted,
and no PPSSPP MCP tools are exposed in this chat. No config or live helper changed.
An in-memory MCP screenshot call with synthetic1x1 raw pixels reproduced installed0.2.0
returning4raw bytes as image/png. Evidence:
local/mcp-ppsspp/capture-protocol-study-1792281804683.json. No network/emulator use.

Proposed correction and protected controller integration are written in
docs/superpowers/specs/2026-10-18-demand-driven-capture-design.md for user review.
Current Destiny trial remains idle at sequence2; capture work does not supersede it.

## Approved capture implementation

User approved the capture design. Plan:
docs/superpowers/plans/2026-10-18-demand-driven-capture.md.
Production modules: demand_capture.py and capture_mailbox.py; debugger.py adds scoped
read_render_png. MCP server tools/ppsspp_capture_mcp.mjs uses the existing installed
Node SDK and a trial-bound local mailbox, never a second debugger connection.
New private capture_handoff.py integrates capture with the existing Standby helper
through static Handoff injection; it must only run in a new protected launch.

Full offline source suite initially1139passed/1existingWindows privilege skip;
7Node tests, strict mypy33modules, Ruff, wheel/CLIhelp passed. A further actual synthetic
Node/Python/service round-trip passed. Independent review found two Important concurrency
issues (request hardlink publication window; complete capture/memory serialization)
and a Minor reason-whitespace mismatch. Fixes and regression verification in progress;
do not activate until review clears. No live capture, gameplay input or commits.

Latest18October process inventory found PPSSPP no longer running; the former helper
has no error files/stderr. Do not infer why the emulator closed. Earlier ready/PID
descriptions are historical. Require current inventory and fresh verified backups
before any capture-enabled launch; do not attach/replay the previous runtime.

## Stop boundary and exact next step

Account check reached99% used in the five-hour window; prior handover requires no new
substantial work below10% remaining. Do not start the live capture trial in this turn.
Original review findings fixed with regression tests: helper-wide serialization,
publication re-stat handling, and exact reason preservation. Narrow follow-up found
helper lock waiting outside the capture deadline; the helper worker is making the final
bounded correction and regression test. Confirm its result/re-review before activation.

Next session: read this note and final agent results, check Git and actual process state.
Require complete checks and no Important findings, then fresh original SYSTEM backup plus
Launcher full original/portable SAVEDATA/PPSSPP_STATE/config backups. Start new private
capture_handoff.py with new empty evidence directory (same CLI as standby_handoff.py).
Wait for ready.json and capture-ready.json. Use an actual MCP SDK client/stdio server
tools/ppsspp_capture_mcp.mjs with the exact mailbox_root and trial_id from capture-ready.
Request one screenshot with an explicit visual reason, inspect its local PNG and verify
pause restoration and preservation. Do not enable the old upstream screenshot handler,
reconnect, use output fallback, or hot-patch/reuse the old session. On download failure stop.
Until acceptance, automatic screenshot readiness stays unchecked. All code/docs uncommitted.

## Resumed after allowance reset

Final queued-deadline regression reproduced RED, then corrected capture_handoff.capture:
deadline starts before investigation-lock acquisition, wraps the whole operation and
passes remaining time to DemandCapture. Queue expiry disables investigation with no later
capture. All162 private helper tests pass; full configured source suite1142passed and
1existingWindows privilege skip. Node7tests, Ruff whole/private, strictmypy33modules pass.
Independent narrow re-review confirms all findings resolved; no remaining actionable issues.

Current PPSSPP-closed guard passed. Fresh original SYSTEM SHA-256 backup:
backups/capture-original-config-20261018T053338Z-1001724d384e4632bcd099df74e8a7a8.
Started new capture_handoff.py helperPID5156 at15:33Brisbane (historical, verify actual).
Run local/move-attack-trial-20261017/capture-run-20261018T1533505495;
active-capture-run.json and active-destiny-run.json point there. Protected Launcher is
preparing fresh complete original/portable save/state/configuration snapshots before launch.
No screenshot requested yet. Require ready.json and capture-ready.json before MCP request.

## Protected live MCP result — 15:37 Brisbane

Fresh four-directory save snapshots and portable config verified under trial
20261018T053359413586Z-ae56ec744bb8455794ab524908edc2f3. Two baseline samples passed;
capture-ready.json issued. Exactly one actual MCP SDK stdio tool call used
ppsspp_capture_screen with an explicit acceptance reason. It reached the existing
controller, then PPSSPP renderColor returned RuntimeError: Could not download output.
No PNG was accepted. Handoff disabled all reads; no reconnect/retry/output fallback,
game input, save/load or automatic closure. PPSSPP PID14640 remained open at stop.
The PNG URI protocol correction is implemented but does not fix this backend failure.

Independent capture-preservation.json verifies SHA-256 inventories for all four snapshots,
both original save/state sources, portable configuration snapshot, original SYSTEM source
and its fresh snapshot. Active portable source comparison intentionally omitted because
the runtime is writable; no trial data was copied back to originals.

The assistant asked for normal human closure (leave any save/discard warning untouched)
before a fresh protected session. Await that response; do not reuse disabled helper.
Automatic GPU/MCP capture remains unverified. The demonstrated built-in screenshot menu
route may be automated through supported Computer Use in a fresh trial; no need to ask
the human to upload an image where the agent can trigger and collect that file itself.

## Supported menu capture passed — current active session

User closed the failed GPU trial normally. Fresh original SYSTEM backup:
backups/menu-capture-original-config-20261018T053914Z-5c31dde491bf484e8f3ecb79f1b541ce.
New standby_handoff.py run: local/move-attack-trial-20261017/menu-capture-run-20261018T1539156648.
active-menu-capture-run.json and active-destiny-run.json point there. Original GPU
active-capture-run.json still describes the failed run; do not use it for current actions.
Trial20261018T053921174534Z-dd5642bd8fe6466292316b462b3d2a40 passed fresh full four-directory
save/state and portable config backups, then two baseline samples; ready at15:42Brisbane.
PPSSPP PID4612 and helperPID19076 are historical identifiers; verify actual state.

Computer Use observed the actual window/menu via accessibility only. Alt+D opened Debug;
unique Take screenshot command was selected with t. No game action, debug break/reset,
GPU request or native-desktop image was used. New ULJS00460_00000.jpg was collected,
944x541/89536bytes, SHA25619c1df462d7fe160bad7ecad8d137acaac80076bf41c60ed92f238b35afe3629.
Its copy in evidence/menu-capture-001.jpg was decoded and visibly accepted: real map/grid
and deployed sprites. Metadata distinguishes built-in JPEG from failed MCP GPU capture.
Menu closed normally, helper remains enabled and idle at sequence2. Preservation hashes
passed for originals, all snapshots, original SYSTEM and config snapshots; see
menu-preservation.json. No copy-back, game input, save/load or commits.

Current next step: awaiting fresh user ready after opening Destiny Unit/Info HP5200 EN230.
User has been asked via async question; no upload required. Publish sequence2 unit-baseline
human_ack only after actual ready. Then original approved down-one-preview/Move/Standby
stages. Agent may trigger built-in screenshots only for new/ambiguous UI evidence using
supported Computer Use. Do not claim unattended runtime capture or working MCP GPU capture.

## User requests independent cursor/menu/Info navigation

User explicitly requested the agent navigate to Destiny, open its command menu, choose
Info and capture, rather than ask for human-ready screens. This authorizes that bounded
navigation but not Move/Attack/Standby execution. Proposed design is in
docs/superpowers/specs/2026-10-18-independent-info-navigation-design.md.

Attempted existing supported Computer Use controls in the current freshly backed-up
menu-capture trial. Confirmed controls.ini keyboard Circle=NKCODE_X52, Cross=Z54 and
arrows19..22 using pinned PPSSPP1.20.4 KeyCodes.h. Sent Right, Right, Down, x with
accessibility refreshes and fresh built-in verification frames00001/00002/00003.
No cursor/menu transition was visibly accepted; images remained map-only. Do not claim
successful navigation, assume a specific cursor position, or repeat the same uncertain
sequence. A focus diagnostic click on observed root window failed with
"coordinate input geometry is unavailable". No coordinate action was accepted.
Cause (tap duration, focus or another issue) is not proven. Native Windows menu keyboard
control continues to work. No new memory request was published; helper still at sequence2.

PPSSPP-specific MCP input tools are not exposed in this chat. Recommended next change is
a narrow timed-input bridge through the existing protected controller, not a second
generic debugger client. Await design approval before implementing this new input behavior.
