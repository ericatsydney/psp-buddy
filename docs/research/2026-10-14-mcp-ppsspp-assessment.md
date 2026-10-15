# mcp-ppsspp assessment — 14 October 2026

## Map-inspection implementation session

The user approved the written map-inspection design and implementation on 14 October 2026,
with a stop condition below 10% remaining five-hour account allowance. Baseline verification:
545 offline tests, Ruff and strict mypy pass. A restricted pytest run failed because Windows
sandbox denied access to pytest-created temporary directories; unrestricted offline rerun passed.

Preserved RAM analysis found all 20 later samples of `0x08E90000..0x08E94FFF` byte-identical
to the prior full snapshot slice. Candidate table origin `0x08E8F690`, stride `0x50`, yields
90 plausible stat/form records with matching self-index fields among the first 512 entries.
Known Gundam 00 and Shenlong record indices are 217 and 143 under that hypothesis. This is
structural research evidence only; no deployment, side, coordinate or action binding follows.
Exact 32-bit pointer searches for the known record addresses found none in the prior full
24 MiB snapshot. Raw analyses remain ignored in `local/map-research-20261014-agent/`.

Protected discovery trial `20261014T083302514611Z-0e02c7be15d6458983d3258d71f5bb9e`
completed fresh full original/portable save/state and configuration backup verification,
then launched the owned isolated runtime. Supported Windows menu observation succeeded,
but click/capture recovery reported unavailable geometry and missing foreground process ID.
The owned emulator process disappeared before a frame was accepted. No cursor/battle input,
RAM sample or MCP call occurred in that trial. The helper stopped and final source, immutable
snapshot and archived-runtime preservation checks passed. Cause of process disappearance
is unproven; do not classify it as a GPU crash or claim native capture success.

A separate freshly backed-up memory-only trial
`20261014T084029300668Z-0ffa88aef38c4ed4995759d13921def4` passed. The installed MCP's
two exact 80-byte mech/pilot records equal the same-trial protected Python reads. Known
values match prior visible calibration: HP 5000/5000, EN 121/210, SP 55/95, level 36,
will 150. MCP reported PPSSPP v1.20.4 and ULJS00460 game version 1.01. The Python
observation scope resumed CPU/UI before closing its socket; MCP ran afterward without
another controlling client. Both MCP processes and owned PPSSPP closed; final original,
snapshot and archived-runtime preservation verification passed. This establishes actual
MCP known-record read compatibility, not map decoding or complete live observation.

The new offline core decodes explicit bounded named records, preserves unknown fields,
and always reports `named_records_only`, unauthenticated supplied provenance and autonomous
unavailability. It does not create tactical Snapshot. Core tests observed red before code;
9 focused tests, Ruff and strict mypy pass after root review corrected zero-capacity EN/SP
handling to match existing reader behavior. Complete tactical/map acceptance has not passed.

Session verification:603 offline tests, Ruff, strict mypy (21 source files), wheel build,
CLI help, retained MCP-evidence inspect-map demonstration and diff check pass. The CLI demo
reports the known mech HP/EN and separate pilot SP while map coordinates/side/deployment
remain unknown. `run` still refuses live execution. Final independent whole-working-tree
review remains pending at the usage-limit handover; core root review passed. Latest account
check reached10% five-hour remaining, so no new trial or major task is started.

Historical initial review: the user requested a repository review and plan update from clean
`f437f30`. At that point only sources had been reviewed; no emulator trial had occurred.
The subsequent protected live memory comparison is recorded above. Initial upstream links
reference mutable `main`; the installed artifact and hashes below define the tested package.

## Installed package and offline study, 14 October 2026

The user subsequently requested installation and memory/map research. Installed exactly
`mcp-ppsspp@0.2.0` under ignored `local/mcp-ppsspp`, using npm with lifecycle scripts
disabled. Node v24.14.0 satisfies its Node 22+ requirement. The npm lockfile pins dependencies;
package integrity is `sha512-Jg+MCwP4oCP+qXS4TlML/SWRpjW4D7zsuMmZecFM26XB8KqdHqMF2fSL6DdYwPsrs5U4XOhcMgQHsVFVUp7PRg==`.
Installed compiled SHA-256 hashes:

| File | SHA-256 |
| --- | --- |
| `dist/index.js` | `4b35d0114e896a86f3041f9092b66dc3b71b2d3e1cbfe24d0d8367b4ea6135e7` |
| `dist/tools.js` | `988845642c67c5560fcdfe8b430004150d72f54475f2dcb55c1cfb688378d37c` |
| `dist/ppsspp.js` | `e2744e36ba7c18cd7564904dea8446a6aa7cb5d203842f1b2ac8e1f836cd58eb` |

Project `.codex/config.toml` registers the installed entrypoint with loopback host and only
ping, game info, typed numeric reads and bulk reads allowed. `codex mcp get ppsspp --json`
confirms registration. Automatic startup is disabled: upstream starts a debugger connection
immediately, so static registration cannot enforce a fresh backup and owned-launch gate.
At installation time no emulator was launched or connected. The later protected memory trial
verified live reads as recorded above; registration alone does not establish tool availability
in an already-running conversation.
The tool filter applies to this Codex client, not to every possible client of the package.

## Continuation, 15 October 2026

Final session checkpoint: a separately backed-up reload
`20261015T013217147892Z-d310387778964f1b96254e5b7fc2f641` retained five frame/RAM pairs.
Vertical cursor candidates reproduced: u16 `0x096007C6` = 4/5/4 after down/up, and
`0x096007CA` = 144/176/144; X remained17 and spatial X560. A later Up from the status
panel moved the cursor to stored row3, spatial Y112. Visible viewport position differs by
one row from the candidate stored coordinates; do not guess camera/world origin.
The named panel corroborated Gundam 00 / Setsuna HP5000, EN121, level36 and will150.
Cross was a status/cancel action here; the recorded successful Info-menu recipe uses Circle.

The installed MCP process returned0 and its two retained 80-byte records matched the final
Python RAM sample. A subsequent console print raised UnicodeEncodeError for Japanese title
text under cp1252; this is a helper reporting failure, not a failed memory comparison.
Final owned-emulator closure and source/configuration/snapshot/archive preservation passed.
Use `-X utf8` for future research helpers. No production code was changed today; baseline603
tests, Ruff and strict mypy pass, and independent review found no Critical/Important issues.
Complete deployment, unit positions, affiliations and action status remain unverified.

The Windows Application Error log confirms an access violation (`0xc0000005`) in yesterday's
owned PID5508 at18:36:20+10:00, module offset`0x864414`. This establishes an emulator crash,
but not its code-level cause. The relevant screenshot/backend settings matched the working
13 October configuration: ScreenshotMode0, JPEG, D3D11 and buffered rendering.

Fresh protected trial `20261015T012546647014Z-21454d99fc34438b84254e5277322275`
obtained three nonblank944x541 built-in JPEG frames using observed Debug menu keyboard
navigation (Alt+D, then unique Take screenshot selection). Native Windows frame capture
still timed out. Each frame has a matching bounded45-second-scope24MiB user-RAM sample.
Visible cursor movement was baseline, one tile right, and one tile left restored; no unit
movement or battle action occurred. Screenshot/RAM pairs are stationary research correlations,
not atomic tactical observations.

The trial stopped when a research helper read an action JSON file during non-atomic
publication. `process-diagnostics.json` records a live process before cleanup and JSONDecodeError;
this was not another proven emulator crash. Owned cleanup and final original/configuration/
snapshot/archive preservation passed. Future action handshakes use completed temporary files
renamed atomically into place, never direct writes to watched action filenames.

Offline ABA analysis identifies u16`0x096007C4` with17→18→17 and u16`0x096007C8`
with560→592→560 (=32*x+16). Nearby u16`0x096007C6` stays4 and`0x096007CA` stays144;
vertical meaning is unvalidated. RAM-top duplicates appear temporary/stack-related. These
values changed during cursor-only motion, so they must not be bound as unit coordinates.
Visible viewport row versus stored row still needs camera/origin corroboration. Exact binary,
image, hash and analysis evidence remains ignored in the trial and`local/cursor-diff-20261015/`.

Current baseline603 tests, Ruff and strict mypy pass. Independent whole-working-tree review
found no Critical/Important issues; Minor historical documentation contradictions were corrected.
The continuing goal is reliable capture plus visibly corroborated deployment/coordinate
research, with held-out validation before operational use. The original10% remaining stop
condition continues. All changes remain uncommitted.

Capture source comparison found that PPSSPP v1.20.4 `type: "base64"` returns raw pixels with
width/height/format/flip metadata, while URI output is PNG. The installed MCP0.2.0 screenshot
handler forwards base64 directly as image/png without converting the raw pixels. Treat this
as a source-established protocol mismatch, not a locally verified working image path.
Both response types share framebuffer download, so switching encoding cannot by itself
resolve the earlier "Could not download output" failure. Do not accept raw pixels as PNG.
[PPSSPP source](https://github.com/hrydgard/ppsspp/blob/v1.20.4/Core/Debugger/WebSocket/GPUBufferSubscriber.cpp)
The Windows resource defines Take Screenshot without a dedicated accelerator. Observed
menu keyboard navigation is an alternative to unavailable click geometry, using only the
supported computer-use API and verifying each resulting state.
[Windows resource](https://github.com/hrydgard/ppsspp/blob/v1.20.4/Windows/ppsspp.rc)

`node local/mcp-ppsspp/study.mjs` uses the MCP SDK's in-memory transports and synthetic replies,
without sockets or emulator startup. It discovers 24 tools and verifies typed u16 output
and bulk hex output. Results are retained in ignored `local/mcp-ppsspp/offline-study.json`.
The suspected `value`/`uintValue` mismatch is an upstream comment error, not a v1.20.4
typed-read protocol bug: the actual PPSSPP source emits `value`.
[PPSSPP v1.20.4 memory implementation](https://github.com/hrydgard/ppsspp/blob/v1.20.4/Core/Debugger/WebSocket/MemorySubscriber.cpp)

## Efficient map research workflow

The installed package offers no memory search, snapshot diff or tactical-map decoder.
Use it for bounded interactive reads; use local analysis for search/diff rather than filling
the conversation with megabytes of hex. Initial known-fixture checks for a future protected
trial are:

```json
{"tool":"ppsspp_read_range","arguments":{"address":149502560,"size":80}}
{"tool":"ppsspp_read_range","arguments":{"address":149594176,"size":80}}
```

These addresses are `0x08E93A60` (named mech inspection) and `0x08EAA040` (named pilot
inspection). Existing decoders and profiles define the field offsets; these are fixture-bound
addresses, not portable roster/map pointers. Verify decimal/hex conversion before a call.
Use `read16` at `0x08EAA07C` for a small SP sanity check, but prefer one bulk record read
when comparing several fields. Require exact byte counts and reject malformed/missing data;
upstream bulk formatting does not itself prove requested-length integrity.

Recommended research sequence, with every emulator trial separately backed up:

1. Establish the protected owned session and exact game/emulator identity before starting
   MCP; ensure the existing Python controller is not simultaneously issuing inputs.
2. Corroborate known named records first. Save raw bytes, addresses, timestamps, trial identity
   and hashes privately. Keep original captures alongside analysis output.
3. Take bounded region samples around established records, then search offline for repeated
   layouts and pointer candidates. Adjacent stat records do not prove deployed units.
4. During separately reviewed bounded trials, compare before/after samples for one visibly
   confirmed cursor tile change or one information-panel selection. Separate cursor coordinates
   from unit coordinates: the former should change while stationary unit records remain stable.
5. For candidate unit tables, validate count, stride/pointers, unique identity, side, active status
   and positions against multiple visible allies/enemies. Require negative examples from reserve
   or inactive entries. A plausible HP pattern alone is insufficient.
6. Bind map width/height, tile order, terrain IDs and occupancy only after visible corroboration
   across several tiles and another map/reload. Validate weapons, movement/legal-action state
   and phase separately; coordinates alone cannot enable the tactical planner.
7. Use coherent protected Python observation scopes for multi-block datasets. Separate MCP reads
   while the game runs are not one atomic snapshot. Current narrow MCP configuration intentionally
   excludes pause/resume; do not bypass it to manufacture coherence.

The existing 0x5000-byte region starting at `0x08E90000` can be obtained in one bulk request
for development comparison, but its roughly 60 KiB hex output should stay in private evidence.
For broader discovery, prefer 4–16 KiB bounded chunks analyzed locally. No whole-RAM chat dump,
assumed stride, guessed text encoding, RAM writes or unvalidated operational map binding.
This sequence is a research proposal; no new map fields have been discovered in this session.

For a later enabled session, supply the actual protected listener port through `PPSSPP_PORT`.
Enable only while a fresh backup/owned session is valid, then disable and stop the server before
closing that session. Persistent automatic activation needs a reviewed launch-gated integration.
[Codex MCP configuration](https://developers.openai.com/codex/mcp/)

## Verified upstream observations

The server uses stdio MCP and PPSSPP's WebSocket debugger, requires Node 22+, accepts a host
and required port, and has no save-state API. It is MIT licensed.
[README](https://github.com/dmang-dev/mcp-ppsspp#readme)

The screenshot handler defaults to renderColor, requests base64, polls stepping state and
attempts restoration. It warns that output capture can crash PPSSPP; restoration errors are
swallowed. Typed memory handlers read `value`, while the transport comment illustrates
`uintValue`: verify actual replies before relying on typed results. Writes, reset and
persistent inputs are exposed.
[Tool implementation](https://github.com/dmang-dev/mcp-ppsspp/blob/main/src/tools.ts)

The client correlates tickets, polls CPU state for control transitions, ignores broadcasts
and reconnects on demand. These mechanics do not establish a protected game session.
[Client implementation](https://github.com/dmang-dev/mcp-ppsspp/blob/main/src/ppsspp.ts)

Startup attempts a connection before serving stdio, even though tool inventory can remain
available following connection failure. Do not start it against a real emulator before the
project's backup gates.
[Startup](https://github.com/dmang-dev/mcp-ppsspp/blob/main/src/index.ts)

## Project fit and recommendation

PSP Buddy already implements bounded direct debugger input, bulk RAM reads, pause ownership,
identity/owned-process checks and uncertain-outcome stops in `src/psp_buddy/debugger.py`.
`capture.py` collects validated screenshot files, but its demonstrated trigger still needs
interactive Windows menu control. Previous protected trials failed with both GPU paths.
See [existing evidence](2026-10-10-hybrid-feasibility.md) and
[current plan](../superpowers/plans/2026-10-10-autonomous-battle-mvp.md).

Inference: the most useful near-term contribution is a reference recipe to compare with
the failed capture requests, especially response encoding. It is not evidence that a
different encoding fixes the backend. Keep the Python runtime and test this hypothesis
under the existing gates; stop if no meaningful difference is found.

Interactive MCP inspection could later assist address discovery and screen/RAM correlation.
It cannot supply validated roster identity, tactical legality, checkpoint completion or
autonomous battle behavior. Its results must enter the same evidence-validation process.
Registers/breakpoints are possible research tools, but expanding to them is outside the
current recommended scope.

Direct upstream use would bypass project-specific protection unless wrapped. A protected
interface needs launch-issued session binding, loopback enforcement, identity validation,
restricted tools, serialized control and explicit cleanup failures. Reconnect must invalidate
observations and pending actions. Installing a generic server alone provides none of these
project guarantees.

## Decision and acceptance

The plan adds M1 offline comparison, M2 conditional capture work and protected held-out
validation, and M3 optional discovery research. The requested local MCP installation is now
complete; the Python runtime has no new dependency. M4 below prioritizes map discovery.
Successful capture must preserve original/backup hashes, supply a visible validated fresh
image and retain or restore the correct pause state. Capture failure leaves unattended
observation unverified. Live checkpoints and complete tactical decoding remain separate gates.
