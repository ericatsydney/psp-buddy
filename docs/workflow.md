# Simple session workflow

Agreed reporting preference, 18 October 2026 (Australia/Brisbane).

## Start and end of a session

Read AGENTS.md, docs/progress.md and the latest handover. Check Git status before work;
verify actual emulator/helper state before any live continuation. Report only:

1. Long-term goal and function checklist.
2. Short-term game-rule/memory investigation checklist.
3. Today/session goal, normally one to three tasks.

Keep this brief. Explain blockers, verification and implementation details when asked;
still perform required protection, checks and review. Tick only ready items and state
the scope when evidence is offline or human-controlled. Do not estimate a completion
percentage from test counts. At session end update progress and leave an exact resume
step with evidence pointers in the handover. No dashboard or scheduled report required.

## Reduce effort

- Consult retained evidence before repeating discovery or asking for another screenshot.
- Give each investigation one question, expected distinguishing observations and a stop
  condition. Prefer offline analysis before a live trial.
- Reuse established field bindings and defining code paths. A matching candidate byte,
  plausible value or cheat label does not prove a game rule.
- Capture meaningful transitions, new UI facts and ambiguous outcomes. Preserve required
  forecasts and stability checks; avoid redundant uploads of unchanged screens.
- Save full evidence locally and report a concise result. Distinguish automatic capture,
  human acknowledgement and human-supplied images; none substitutes for another silently.
- Continue within existing approved scope without repeated permission questions. Request
  human involvement only for a necessary decision or a step automation cannot yet perform.
- Extract reusable sanitized helpers from private experiments when needed, keeping saves,
  RAM dumps, private profiles and raw evidence ignored. That is future implementation work.

## PPSSPP MCP review — evidence from 15–17 October

Reviewed the installed mcp-ppsspp 0.2.0 code, local registration, retained probe/study,
trial helpers and research notes. No MCP server or emulator was started for this review.

What we learned:

- MCP bounded mech/pilot reads matched protected Python reads. Use typed reads for a
  focused field and bounded range reads for nearby data; analyze bytes locally rather
  than returning large hex dumps to chat. It has no built-in memory search, diff,
  game-rule decoder or save-state tool.
- On 15 October, PPSSPP's built-in screenshot command produced usable JPEG frames through
  supported Windows menu navigation. This is the demonstrated fallback; it still needs
  supported UI control and fresh-image validation.
- The installed MCP screenshot handler requests `type: "base64"` and returns it as
  `image/png`. PPSSPP 1.20.4 supplies raw pixels plus format/flip metadata in that mode.
  `type: "uri"` supplies an encoded PNG. The installed handler therefore cannot be
  accepted as a working PNG capture path without correction and validation.
- Changing encoding does not fix a framebuffer download failure: download precedes
  encoding. Do not repeat encoding variations after the same download failure.
- Screenshot handling may pause/resume; installed code suppresses restoration errors.
  Do not run it alongside the Python observation controller or assume restored state.
- On 17 October, JIT markers caused instruction fingerprint mismatches. The dedicated
  Python original-code reader resolved this while retaining exact checks. Generic MCP
  range reads are not a replacement for that verified code-reading path.
- Atomic request-file publication avoids the partial-JSON failure seen on 15 October.
  Run/stage-bound requests also prevent replaying acknowledgements across restarts.
- The ready-only helper already reduced images for some stages; forecasts still required
  images. Reuse this supported mode where applicable rather than inventing evidence.

Recommended division of work:

1. Keep launch/backup protection and coherent multi-block observations in the existing
   Python controller. Separate MCP reads while the game runs are not one coherent snapshot.
2. Use MCP for targeted interactive inspection under a verified protected session. The
   local registration is disabled and allows only identity/read tools; screenshot,
   pause/resume and input are not currently enabled. No configuration was changed here.
3. Next capture work: design a protected MCP bridge/correction that requests PNG URI
   output, validates a decoded fresh image, serializes controller ownership, and reports
   pause restoration failures. First use offline protocol fixtures, then a freshly
   backed-up bounded live trial. URI is a candidate, not a proven GPU fix.
4. Compare render-buffer output against the actual visible screen before accepting it
   as a substitute. Avoid switching automatically to the output-buffer path on failure.
   If capture fails, stop that attempt and use the demonstrated built-in screenshot
   route only within the approved trial scope.
5. After reliable capture, calibrate bounded input recipes separately. Timed MCP presses
   return before the requested frames necessarily finish; verify each transition and
   release controls. Do not automate battle choices from timing alone or enable all tools.

The intended benefit is automatic local screenshots and focused memory inspection, followed
later by validated navigation. Human uploads and repeated ready messages can then decrease
without weakening evidence or save protection. No live MCP improvement is claimed yet.

Evidence: [MCP assessment](research/2026-10-14-mcp-ppsspp-assessment.md),
[map summary](research/2026-10-16-map-evidence-summary.md),
[Move/Attack trial](research/2026-10-17-move-attack-trial.md),
[ready helper](superpowers/plans/2026-10-17-ready-checkpoints.md), and
[latest handover](research/2026-10-17-session-handover.md).

Source check: [PPSSPP 1.20.4 GPU buffer protocol](https://github.com/hrydgard/ppsspp/blob/v1.20.4/Core/Debugger/WebSocket/GPUBufferSubscriber.cpp).
Installed MCP dist/tools.js was inspected directly; upstream main may differ.
