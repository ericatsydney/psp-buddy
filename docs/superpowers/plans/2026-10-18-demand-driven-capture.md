# Demand-driven capture implementation plan

**Goal:** Correct PNG capture exposed through MCP, using the existing protected controller,
only on explicit visual need. No changes to the running Destiny process or upstream package.

**Architecture:** The bound debugger adapter provides a scoped renderColor URI operation.
A project-owned capture service validates/persists PNG and metadata. A bounded file mailbox
lets an MCP SDK stdio bridge request capture from that same controller; the bridge never
connects to PPSSPP directly. Enable only in a new protected helper session.

**Stack:** Python asyncio/Pillow/pytest, existing debugger/Launcher; installed Node MCP SDK.
No new runtime dependencies, commits or MCP registration changes.

## Task 1 — adapter (delegated, disjoint write scope)

- [ ] Write tests/unit/test_debugger_capture.py; observe missing scoped read failure.
- [ ] Add DebuggerAdapter.read_render_png() -> dict[str, object] in src/psp_buddy/debugger.py.
  Require the current task to own the bound observation pause and operation lock. Send
  only gpu.buffer.renderColor with {"type":"uri"}; verify bound identity at send time.
  Refuse uncertainty and wrong-task calls; latch protocol/transport failures. Preserve
  existing observation_pause semantics and surface cleanup errors. No automatic retry.
- [ ] Verify focused debugger unit tests, Ruff and strict mypy.

## Task 2 — capture service and MCP bridge

- [ ] Write tests/unit/test_demand_capture.py first. Use issuer-created synthetic sessions
  and fake transports, never a real emulator. Prove no construction-time capture;
  demand-only valid PNG storage; raw/malformed/oversize/blank/dimension errors;
  unchanged-screen fresh acquisitions; failures latch; wrong session rejected;
  pause restoration failure produces no accepted result; serialized requests.
- [ ] Implement src/psp_buddy/demand_capture.py. Expose capture(reason, timeout_seconds),
  accept an already bound adapter/session, own an asyncio lock and observation scope,
  validate PNG URI with Pillow, save unique trial/sequence files plus JSON metadata.
  Bound reason/bytes/dimensions/time; no user-selected filesystem output paths.
- [ ] Write tests/unit/test_capture_mailbox.py first, then src/psp_buddy/capture_mailbox.py.
  Strict trial/request IDs and schema; bounded atomic publications; replay rejection;
  one outstanding request; return only local metadata or explicit error. The capture
  controller owns a new empty mailbox under the current trial's evidence directory.
- [ ] Add tools/ppsspp_capture_mcp.mjs using installed MCP SDK, one screenshot tool only.
  Validate input, publish atomic request, await matching response, return path/metadata
  only. No PPSSPP socket, inputs, pause controls or automatic retry. Test via Node's
  test runner with a synthetic mailbox worker in tests/node/capture_mcp.test.mjs.
- [ ] Add a private new helper entrypoint under local/, using reviewed existing Launcher
  and static dependency injection; do not edit/hot-patch the waiting Destiny runtime.
  If integration needs a small extension seam, test it before changing the helper.

## Verification and review

- [ ] Focused red/green: .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
  tests/unit/test_debugger_capture.py tests/unit/test_demand_capture.py
  tests/unit/test_capture_mailbox.py --basetemp local/pytest-demand-capture-<unique>.
- [ ] node --test tests/node/capture_mcp.test.mjs (synthetic MCP and filesystem only).
- [ ] Full configured pytest suite, Ruff check ., strict mypy src/psp_buddy,
  pip wheel --no-deps --no-build-isolation . into a new ignored local output folder,
  CLI --help. Expected: all pass; report existing platform skips.
- [ ] Review git diff HEAD plus new files against the approved spec. Independent
  review after required checks; fix Critical/Important findings and rerun affected checks.
- [ ] Update usage, progress and handover. Keep automatic-capture checkbox unchecked
  until one fresh protected live trial proves a correct image and state preservation.

## Live acceptance boundary

Preserve the current open Destiny session. Ask for normal human closure only when the
reviewed result is ready for activation; do not discard unsaved state or dismiss warnings.
Then create fresh full SHA-256 original/portable save/state/configuration backups via
the existing Launcher and activate the new capture-enabled helper. Collect one demanded
image, inspect it and confirm pause state and save preservation. On download failure stop;
do not try output framebuffer or reconnect. Live verification remains incomplete until
this boundary is satisfied. No additional implementation approval is needed within scope.

## Implementation checkpoint

Adapter, capture service, bounded mailbox, MCP stdio server and private capture-enabled
helper implemented with observed failing regressions before fixes. Final source suite:
1142pass/1existingWindows privilege skip; private helpers162pass; Node7pass; Ruff,
strictmypy33modules, wheel and CLIhelp pass. Independent review findings fixed and
re-reviewed clear, including helper queue timeout covering lock acquisition.
Live acceptance is now starting under fresh protected backup gates; not yet complete.
