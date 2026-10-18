# Capture only when investigation needs visual evidence

Status: proposed for user review; no capture implementation or live capture trial yet.

## Goal and scope

Reduce manual screenshot uploads and repeated ready requests during game-rule/memory
research. Use retained evidence and coherent memory observations first. Capture a fresh
screen only for a new UI fact, ambiguous state, required forecast, or visible milestone.
This does not authorize automatic gameplay, alter existing human-only diagnostic requests,
or establish action legality from an image alone.

## Options and recommendation

1. Enable the installed MCP screenshot unchanged: rejected. A synthetic in-memory MCP
   call reproduced raw pixels returned as image/png, and pause restoration errors are hidden.
2. Recommended: expose corrected MCP capture through a protected session bridge, with
   capture serialized by the existing observation controller. Request renderColor PNG URI
   output, validate the image, and propagate restoration failures. Preserve installed
   upstream files and keep changes in a reviewed project-owned adapter.
3. Supported PPSSPP menu screenshot collection remains the demonstrated fallback. It needs
   more UI coordination. Use only when allowed by the current protected trial; do not
   cascade framebuffer requests automatically after failure.

## Interfaces and data flow

Investigation requests capture(reason) only when existing evidence is insufficient.
The bridge requires launch-issued session identity, valid backup receipt and exclusive
controller ownership. It queries/retains prior pause state, captures a PNG URI through
the pinned debugger protocol, validates and stores it locally, restores prior state,
and returns a small path/metadata result. The MCP-facing tool calls this protected
operation rather than opening a competing unrestricted debugger client.

Metadata binds trial ID, capture sequence/time, purpose, PNG hash/dimensions and controller
state. Screen/RAM correlation must describe its real timing; do not call them atomic
without proving that property. Allow a deliberate fresh capture of an identical screen:
matching hashes alone do not prove stale acquisition or permit skipping required evidence.

## Failures and exclusions

Reject malformed URI, invalid/blank image, wrong identity, missing protection or unknown
pause state. Bound bytes, dimensions and time. Propagate restore failures and stop further
control when outcome is uncertain. No automatic reconnect, reset, output-buffer fallback,
new input tools, RAM writes, cheats, save/load, or automatic game closure.

Do not hot-patch the waiting Destiny helper or attach a second controller. Preserve the
open game. Any activation uses a separately approved fresh protected session after normal
closure, with complete SHA-256-verified original/portable saves/states and configs.

## Acceptance and verification

Observe meaningful offline failures before implementing: raw-pixel-as-PNG rejection;
valid PNG URI handling; malformed/oversized image rejection; prior paused/running state
preservation; restoration error propagation; exclusive controller and invalid-receipt
rejection; requests only for explicit visual need. No emulator is used in these tests.

After review, one protected live trial must obtain a visibly correct fresh game image and
verify identity, controller state and save preservation. PNG URI encoding does not fix a
framebuffer download failure; stop if download fails. Automatic navigation needs a separate
design and calibration. Until live acceptance, retain existing human-ready collection.

Evidence: local/mcp-ppsspp/capture-protocol-study-1792281804683.json (synthetic, no sockets),
installed0.2.0 dist/tools.js, and the pinned PPSSPP1.20.4 protocol analysis in
docs/research/2026-10-14-mcp-ppsspp-assessment.md.
