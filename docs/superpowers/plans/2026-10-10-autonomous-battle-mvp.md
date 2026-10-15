# Autonomous Battle MVP Implementation Plan

## MCP evaluation update, 2026-10-14

Historical evaluation/initial checklist below. Current implementation, successful protected
MCP known-record reads and remaining map-discovery gates are tracked in
[the map-inspection continuation](2026-10-14-map-inspection.md). Initial unchecked items
below do not override that plan's completed work or imply live reads remain untested.

**Subsequent user request:** install the MCP and study efficient memory/map understanding.
Pinned `mcp-ppsspp@0.2.0` is now installed in ignored `local/mcp-ppsspp` and registered in
project `.codex/config.toml`, disabled pending a protected live session, with six inspection
tools allowed. Offline MCP discovery and synthetic typed/bulk read checks pass (24 upstream
tools discovered). Actual PPSSPP v1.20.4 source confirms typed reads use `value`; the earlier
transport-comment concern is resolved. No live connection or new tactical fields were verified.
These facts supersede the installation deferral in the original evaluation below.

### M4: Efficient memory/map discovery priority

**Files:** research updates in `docs/research/2026-10-14-mcp-ppsspp-assessment.md` and
`docs/research/2026-10-10-profile-validation.md`; raw bytes, diff reports and trial scripts
remain ignored under `local/` and `backups/`. No production reader changes during discovery.

- [x] Install a pinned local package, inspect compiled handlers, verify MCP inventory and
  typed/bulk formatting offline, and register a disabled narrow inspection configuration.
- [ ] Before a live server start, freshly back up complete original/portable save directories
  and configuration, verify SHA-256 manifests and claim a protected owned listener. Verify game
  and emulator identity; do not allow concurrent controllers or automatic reconnect continuation.
- [ ] Read known 0x50-byte mech/pilot records using bulk reads and compare with established
  profiles. Exact byte lengths, identities and private evidence hashes are required.
- [ ] Use preserved regional samples for offline record/pointer search, then gather visibly
  corroborated before/after samples for a single bounded cursor/selection change in a separately
  protected trial. Do not classify a changing coordinate as a unit position without corroboration.
- [ ] Validate active-roster count/stride or pointers, unique IDs, sides and positions across
  several allies/enemies and inactive/reserve negative examples. Validate map dimensions,
  tile ordering, terrain and occupancy across multiple tiles and a held-out map/reload.
- [ ] Keep candidates unavailable to the planner. Before implementing a map reader, present
  the evidence-bound interface/design for explicit approval, update the spec and detailed TDD
  plan, then implement and review bounded tasks. Existing live acceptance gates still apply.

Success for this research is a reproducible field/evidence table and unknown-field list,
not simply MCP connectivity. Use local chunk analysis to reduce round trips and avoid large
hex dumps in chat; use existing protected Python observation scopes for coherent multi-block
samples. Current MCP configuration does not permit pause, input, writes or screenshot calls.

Documentation-only update requested by the user after reviewing
[dmang-dev/mcp-ppsspp](https://github.com/dmang-dev/mcp-ppsspp).
Starting tree is clean at `f437f30`. See the
[source assessment](../../research/2026-10-14-mcp-ppsspp-assessment.md).
This section updates the next-work priority; earlier continuation entries remain historical.
No MCP installation, registration, emulator connection or live trial was performed.

**Recommendation:** retain the protected Python debugger as the production transport.
Use the upstream implementation as a reference for a focused capture investigation.
Evaluate an optional MCP discovery interface only if it offers a measurable workflow benefit.
The existing approved battle scope remains unchanged; a new exposed MCP control interface
requires design/spec review before implementation. `run` remains disabled.

| Approach | Benefit | Cost / decision |
| --- | --- | --- |
| Keep Python; investigate the upstream capture recipe | Smallest change; retains owned-session, identity and cleanup enforcement | Recommended first; successful capture must be demonstrated locally |
| Optional protected MCP discovery interface | Convenient interactive inspection during profile research | Requires a gated wrapper, tool restrictions and evidence export; defer until the capture investigation is evaluated |
| Replace runtime transport with the upstream server | Reuses a general debugger tool interface | Adds Node/MCP integration and requires rebuilding current safety contracts; do not adopt for the MVP |

### M1: Offline protocol and capture comparison (before the next Task 4 trial)

**Files:** inspect `src/psp_buddy/debugger.py`, `capture.py`, `launch.py`,
`tests/unit/test_debugger.py`, `test_transport.py`, `test_capture.py`; record findings in
`docs/research/2026-10-14-mcp-ppsspp-assessment.md`. No production changes in this step.

- [ ] Resolve and record the upstream commit SHA, package version and source hashes before
  using its recipe; the assessment currently references mutable `main`, not a pinned release.
  Compare its event names, image response formats and pause transitions against the actual
  PPSSPP v1.20.4 source and retained private failure evidence.
- [ ] Determine whether the base64 response format supplies a meaningful untested difference
  from existing URI capture failures. A transport wrapper cannot establish GPU compatibility.
  Preserve both prior render/output failures and the successful menu-triggered collector.
- [ ] Write the proposed capture contract into the existing MVP spec for user review before
  implementation: owned launch and debugger binding, bounded decoded image, expected size,
  game/trial identity, monotonic sequence, digest, serialized observation and pause cleanup.
  Define whether render captures require separate recognition calibration.

### M2: Conditional Python capture implementation and protected validation

**Files if M1 justifies a change:** modify `src/psp_buddy/debugger.py`,
`src/psp_buddy/capture.py`, `tests/unit/test_debugger.py`, `tests/unit/test_capture.py`;
create `tests/integration/test_capture.py`; update the MVP spec, this plan and the assessment.
Do not broaden the command allowlist beyond the reviewed image format change.

- [ ] First observe meaningful failing synthetic tests for the newly proposed response format,
  malformed/oversized base64, incomplete/blank/wrong-size images, changed session binding,
  cancellation, concurrent capture/input, retained user pause and failed resume. Existing URI
  behavior and file-collector regressions must remain covered.
- [ ] Implement only the approved format/decoder path using the existing observation scope.
  On uncertain cleanup, prohibit subsequent actions and report the uncertainty. A decoded
  image without a verified bound session must never become an accepted observation.
- [ ] Run focused tests, then full offline verification using the commands below. Review the
  working tree against the updated spec and fix blocking findings before a live trial.
- [ ] Before EACH live trial, confirm PPSSPP is closed or not writing saves; create fresh
  timestamped complete SHA-256-verified original AND portable SAVEDATA/PPSSPP_STATE backups,
  retain manifests, and back up configuration before any change. Backup failure blocks launch.
  Use only the owned portable session; never write to originals or copy trial saves back.
- [ ] Try render capture first, with no battle actions or simultaneous second debugger client.
  Confirm visible frame content, dimensions, identity, freshness and restored CPU/UI state;
  retain private evidence and verify originals/snapshots/archive preservation after closure.
  Stop on capture/cleanup failure; do not automatically switch to output capture or restart.
- [ ] A successful trial is followed by a separate freshly backed-up held-out launch with a
  frozen capture/recognition profile. If either trial fails, retain the file collector and mark
  unattended capture unverified. Do not enable menus or autonomous play from image success alone.

### M3: Optional MCP discovery decision (deferred)

**Documentation:** update this assessment and `docs/usage.md` only after deciding whether
interactive tooling adds value. No package dependency or client configuration is added now.

- [ ] If pursued, review a separate design for a narrow interface backed by PSP Buddy's
  protected launcher/debugger: expose bounded inspection and verified capture only initially.
  Reject RAM/register writes, reset, stepping, breakpoint mutation, analog and persistent holds.
  Timed input, if later approved, must obey existing duration, postcondition and release rules.
- [ ] Require backup/session gates before starting any server that connects automatically,
  even for tool inventory. Use a pinned artifact, Node 22+ if using upstream, loopback only,
  owned endpoint, exact emulator/game/patch identity and one controller at a time.
  Test gate rejection without any socket opening. Disconnect/reconnect requires fresh identity
  and observation validation; never resume stale actions or replay uncertain commands.
- [ ] Export discovery evidence into existing private records; independently validate it before
  extending tactical profiles. No raw game text, RAM, screenshots or saves enter public fixtures.

### Verification and unchanged acceptance gates

For M2 use PowerShell at the repository root, with a new basetemp path on each invocation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_debugger.py tests/unit/test_transport.py tests/unit/test_capture.py -q -p no:cacheprovider --basetemp local/mcp-capture-focused-20261014
.\.venv\Scripts\python.exe -m pytest tests/unit tests/scenarios -q -p no:cacheprovider --basetemp local/mcp-capture-full-20261014
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src/psp_buddy
.\.venv\Scripts\python.exe -m pip wheel . --no-deps --no-build-isolation --wheel-dir local/mcp-capture-wheel
.\.venv\Scripts\python.exe -m psp_buddy --help
git diff --check
```

Expected: all tests/checks pass, wheel builds, CLI help works, and `run` still refuses live
execution until the existing gates pass. Protected integration commands remain those in the
Verification contract below; run the new capture module only through its backup-gated fixture.
The documentation update itself needs link/path review and `git diff --check`, not emulator tests.

Task 4 still needs complete tactical observation and production screen/menu evidence.
Task 6 still needs verified live checkpoint save/load. Tasks 7/10 still need legal-action
postconditions and one-map acceptance. MCP availability passes none of those gates.
Leave all files uncommitted; do not install, register, launch, commit or publish as part of
this planning update.

## Five-hour continuation, 2026-10-13

Start from clean `6ac276b`; the previous session's changes are committed by the user.
Existing written design/implementation approval and no-auto-commit rules continue.
Supported `@oai/sky` initialized successfully and listed current windows; PPSSPP was absent.
The prior native-control limitation must not be assumed to persist.

WIP resume: the first protected discovery timed out at native app approval and preserved
all originals/snapshots. An OpenGL debugger capture trial rejected output; a subsequent
display-ready trial obtained a built-in screenshot but debugger readback still failed and
reported paused UI/CPU state. Its input guard stopped before any game input. All owned
processes closed and preservation checks passed. Resume pilot discovery with the previously
validated D3D11 renderer: `Launcher.prepare(graphics_backend=2)` changes only the newly
backed-up trial configuration. Tests first establish source/config-snapshot preservation and
rejection of unvalidated renderer values; review and full offline checks precede live launch.
Capture/profile work remains the priority; generic executor and offline CLI work is retained.

Fresh D3D11 trial `20261013T120643946751Z-15f21fe525cc490e8f5767bbb5986b90`
closed successfully after seven captures and bounded information-menu navigation only.
Originals, snapshot configuration and archived runtime verified unchanged. Unit/Pilot screens
corroborate named Setsuna SP 55, level 36 and will 150 against fresh pilot-region reads at
`0x08EAA07C`, byte `0x08EAA086` and `0x08EAA07E`. Maximum SP 95 matches u16 at
`0x08EAA05C`. All seven pilot-region samples agree; this is one named fixture,
not deployed-pilot identity, roster or cross-map validation.

- [x] Bounded pilot reader: add immutable `PilotInspectionProfile` in `profile.py` and
  `decode_pilot_inspection` in `reader.py`, with `tests/unit/test_pilot_reader.py`. Reuse
  evidence-bound unsigned field layouts, identity/span/overlap validation; require SP and
  positive level, allow only SP/max-SP/level/will, leave unvalidated optional maxima absent.
  Test malformed bindings, identity/bytes mismatch, invalid level and supplied max-SP bounds
  red before implementation. This never creates a tactical snapshot or guesses pilot identity.
  Root verifies decoding offline against preserved fresh samples after independent review.
- [x] Recognition continuation: unchanged v1 broad landmarks rejected all four fresh info
  frames. Preserve that failure evidence. Calibrate static UI anchors that exclude animated
  background/stat values, preserving strict thresholds and unknown/ambiguous behavior.
  Distinguish recalibration from new held-out validation; run a separate freshly backed-up
  trial for frozen-profile acceptance if needed. Keep templates/raw assets private.

- [ ] Root: protected capture/profile discovery, sequentially. Read current launcher/trial
  helpers, confirm emulator closed, create fresh complete SHA-256-verified original/portable
  save and configuration snapshots, then launch through the owned-session gate. Use supported
  Sky APIs for observed Windows menu actions and the debugger for allowlisted game input and
  coherent read-only RAM samples. Correlate named-unit pilot/resource fields with freshly
  inspected screens; do not guess roster/phase/legal-action data. Investigate a documented
  unattended capture trigger before claiming a standalone bridge. Close the owned process
  and verify originals, snapshots and archived runtime after every trial.
- [x] Executor agent: `src/psp_buddy/executor.py`, `tests/unit/test_executor.py` only.
  Implement Task 7's generic bounded transition engine with immutable evidence-bound action
  recipes and injected observation/input adapters. Require identity, fresh legal-action
  membership, expected screen/menu context and explicit per-step/postcondition evidence.
  Tests cover move/attack, Repair, Trust, wait/end-turn, reactions, decision-free dialogue,
  choices/map-clear, stale evidence, timeout/no-progress, stop/cancellation and release cleanup.
  No guessed production menu sequences; live recipes remain disabled until gates pass.
- [x] CLI agent: `src/psp_buddy/cli.py`, `src/psp_buddy/inspection_io.py`,
  `src/psp_buddy/__main__.py`, `tests/unit/test_cli.py`, `tests/unit/test_inspection_io.py` only.
  Implement read-only `validate --config [--instructions-file]` capability reports and offline
  `inspect --config --record` for bounded inspection-profile JSON and supplied record bytes.
  Missing `--record` cannot silently launch/connect. Strict descriptor identity/type/bounds,
  duplicate JSON keys and unsupported tactical profile claims fail closed. Distinguish supplied
  provenance/calibration from authenticated live evidence. `run` remains refused. Tests prove
  no live imports/connections/save/input, invalid configs/policies/records and useful JSON reports.
- [x] Root reviews both tasks before integration; fix blocking findings, add a composed
  executor/supervisor scenario, run full pytest, Ruff, strict mypy, package/build and CLI checks,
  independently review tracked/untracked working-tree files and preserve private evidence.
- [x] Update this plan, usage/README and research with exact results and remaining gates.

All pytest fixtures use unique ignored `local/` basetemp directories and `-p no:cacheprovider`;
known Windows sandbox directory restrictions may require approved unrestricted offline runs.
Use existing verification commands from the plan. No automatic commit, push, RAM write,
original-save restoration, trial-save copying back or live autonomous runner enablement.

13 October acceptance checkpoint: the reviewed reader matches all seven development and
six held-out pilot samples (SP 55/95, level 36, will 150). Protected held-out trial
`20261013T122746277660Z-523bda9354a74a4d9032f1c875fc5652` classified Unit/Pilot/Mech
with the unchanged frozen static profile and rejected all three map/command frames.
Descriptor SHA-256: `6e22d1b39e247d9abcfc05ab406a1c3e5f84ff0b8fabb3835a232e9976a0e4b2`.
CPU/UI resumed after every observation, input releases acknowledged, owned PPSSPP closed,
and final originals/snapshots/archive preservation checks passed. This validates only the
same named fixture/rendering configuration across independent launches. Standalone capture,
complete tactical observation, live checkpoints and production menu execution remain WIP.
All 545 offline tests, Ruff and strict mypy pass; pilot/executor/CLI reviews have no blocking
findings. Final wheel build and independent whole-working-tree review passed; Minor stale
documentation claims corrected. `validate` and supplied-record `inspect` demonstration passed;
`run` refused live execution. Private evidence/config/game assets remain ignored. All new
work is uncommitted. Root discovery remains incomplete for unattended capture and complete
tactical bindings; this checkpoint does not pass the one-map autonomous acceptance gate.

## Five-hour continuation, 2026-10-12

Existing approved scope and no-commit rules continue. Baseline: 234 offline tests pass with
`.\.venv\Scripts\python.exe -m pytest tests/unit -q -p no:cacheprovider --basetemp local/session-baseline-verified-20261012`.
The restricted Windows sandbox denies access to pytest-created
directories; approved unrestricted offline execution is required, as previously documented.

- [x] Root: create `recognition.py` and `tests/unit/test_recognition.py`. First observe
  missing-module and behavioral failures for synthetic image landmarks, unknown/ambiguous
  screens, mismatched identity/dimensions/digest, and stale sequences. Implement evidence-bound
  multi-landmark pixel matching with conservative thresholds and immutable results. This
  classifies a screen only; it supplies no legal action, decoded text, phase, or tactical state.
  Validate a private inspection profile against preserved Unit/Pilot/Mech captures, including
  cross-screen rejection. Raw templates remain private. Fresh live recognition remains gated.
- [x] Checkpoint agent: implement Task 6 offline contracts in `checkpoint.py` and its unit
  tests, separating command acknowledgement, completion, artifact validation and restored
  game observation. No live save/load adapter is assumed.
- [x] Reaction agent: implement Task 8 pure rules in `reactions.py` and its unit tests,
  requiring sequence-bound incoming context, legal choices and validated predictions.
- [x] Root reviews each task before dependent integration. Then implement bounded supervision
  with synthetic save-before-end-turn and retry scenarios if contracts pass review.
  Files: `src/psp_buddy/supervisor.py`, `tests/unit/test_supervisor.py`, and
  `tests/scenarios/test_battle.py`. Compose existing pure planner/reaction decisions with
  injected trusted observation/execution/checkpoint adapters; keep CLI disabled. Startup
  verifies the existing selected checkpoint without saving; every action consumes current
  legal-action evidence. Save completion and unchanged fresh observation precede end-turn.
  Defeat reload increments retries only after a verified fresh restore; successful enemy
  phase resets budget. Test four failed attempts, failed saves/loads, no distinct reactions,
  scripted departures, stop/cancellation cleanup, map completion, unknown choice, stale
  observations and bounded no-progress. Run focused pytest red before implementation, then
  complete pytest, Ruff and mypy before independent review.
- [x] Run complete offline pytest, Ruff, strict mypy, CLI help and diff checks; independently
  review tracked and intended untracked files. Record evidence and incomplete live gates.

Native application automation is unavailable in this session. Do not launch PPSSPP for a
menu-driven trial that cannot be observed and controlled through a supported interface.
Any later live trial still requires fresh complete verified save/configuration backups.

Continuation result: recognition has 25 synthetic tests and distinguishes the preserved
Unit/Pilot/Mech reference captures while rejecting map/command captures. The preserved stat
record was decoded again into a new ignored evidence file, preserving earlier evidence;
HP 5000/5000, EN 121/210 and the corroborated defense/mobility/accuracy remain consistent.
Checkpoint contracts have 51 tests, reaction rules 58, supervision 26, and the composed
two-turn scenario passes. Shared model dialogue identity has three new rejection tests.
The complete suite passes 398 tests. Ruff, strict mypy (16 source files), CLI help, expected
live-run refusal and diff checks pass. Review fixes cover artifact-to-state binding, slot
bounds, bounded protected paths, any allied defeat, scripted departures, repeated dialogue/
reaction progress, missing roster members and unknown HP before retry reset. Final complete
working-tree review passed after the checkpoint scripted-departure regression fix, with no
remaining Critical or Important findings. No outstanding Minor code findings were reported;
documented calibration/backend/deadline limitations remain. Live Tasks 4/6/7/10 gates remain
unchecked. This completes the bounded offline session milestone, not autonomous battle
acceptance. Changes remain uncommitted at HEAD `5a68ea4`.

> **For agentic workers:** Execute task by task using bounded subagents with disjoint write scopes, reviewing each result before dependent work. The writing-plans skill names `superpowers:subagent-driven-development` or `superpowers:executing-plans`; neither is installed in this session. Follow the available global workflow instead, and disclose that substitution. Steps use checkboxes for tracking. Do not commit any files.

**Goal:** Safely run one Super Robot Wars Z2 Rebirth English v0.8 battle from slot 2, using the approved local strategy, one working checkpoint, and at most three reload retries per checkpoint.

**Architecture:** A local Python CLI composes independent backup, debugger, observation, policy, planning, execution, checkpoint, and supervision services. Pure tactical decisions consume validated snapshots; only the executor issues game inputs. Live execution remains disabled until protected integration gates pass.

**Tech Stack:** Python 3.11 or newer; standard-library filesystem/hash/configuration utilities; `websockets` for the debugger; `pytest` for tests; Ruff for linting; mypy for type checks. Capture/recognition dependencies are selected only after a capture method works in PPSSPP; this plan does not assume OCR is sufficient.

**Approved source:** [MVP specification](../specs/2026-10-10-autonomous-battle-mvp-design.md). [Research evidence](../../research/2026-10-10-hybrid-feasibility.md) records the HP observations and unresolved integrations.

## Starting conditions and execution rules

- Implementation started from clean commit `ca899a4` on 10 October 2026. The repository contained documentation and no application code or configured verification commands. Check status before execution; stop for unrelated changes.
- The user explicitly authorized implementation according to this plan on 10 October 2026. Emulator trials still require all protection and evidence gates below.
- Every live trial, including observation-only debugger tests, needs a fresh verified backup of original and active portable saves. Config changes also need config backups. Follow `AGENTS.md`; backup failure or uncertain save-writing status blocks a trial.
- No memory writes, cheats, automatic original-save restoration, model calls during play, commits, pushes, or publishing.
- Each task below follows red/green/refactor: write the named behavior tests, observe their meaningful failure, implement only the relevant behavior, rerun the focused tests, then refactor with tests passing. Missing imports can prove the initial absence of a module; add a failing behavioral assertion before completing that task.
- Integration discovery is sequential. Unknown capture, profile, or save mechanisms are evidence gates, not permissions to invent working implementations. If a gate cannot be validated, preserve the independently tested software and report the blocked live capability.

## File ownership and public/private boundary

| Files to create | Responsibility |
| --- | --- |
| `pyproject.toml`, `src/psp_buddy/__init__.py`, `src/psp_buddy/__main__.py` | Packaging, CLI entry point, verification settings |
| `src/psp_buddy/models.py`, `config.py` | Typed immutable observations/actions, validated machine configuration |
| `src/psp_buddy/backup.py` | Fresh complete copies, SHA-256 manifests, source stability checks |
| `src/psp_buddy/debugger.py` | Allowlisted WebSocket commands, tickets/events, timeouts, pause/release cleanup |
| `src/psp_buddy/capture.py`, `recognition.py` | Verified image source and recognized screen states |
| `src/psp_buddy/profile.py`, `reader.py` | Profile identity, coherent validated memory decoding |
| `src/psp_buddy/policy.py` | Bounded natural-language parsing and explicit defaults |
| `src/psp_buddy/planner.py`, `reactions.py` | Pure allied tactics and bounded enemy reaction alternatives |
| `src/psp_buddy/checkpoint.py` | Verified same-slot save/load completion and identity |
| `src/psp_buddy/executor.py` | Recognized menu transitions with bounded input and postconditions |
| `src/psp_buddy/supervisor.py`, `cli.py` | Run state machine, retries, stop control, handover report |
| `tests/conftest.py`, `tests/unit/test_*.py` | Synthetic fixtures and isolated behavior tests |
| `tests/integration/test_debugger.py`, `test_capture.py`, `test_reader.py`, `test_checkpoint.py`, `test_executor.py` | Explicitly enabled protected emulator checks |
| `tests/scenarios/test_battle.py` | Simulated full-run safety scenarios |
| `config.example.json`, `docs/usage.md`, `docs/research/2026-10-10-profile-validation.md` | Portable configuration template, instructions, field-validation evidence |

Modify only `.gitignore`, `README.md`, and the approved spec/plan when documentation or exclusions need updating. Raw screenshots, RAM, extracted game strings, logs, local configuration, executable archives, saves, and backup manifests stay under ignored `backups/` or ignored `local/`. Public tests use synthetic values, not dumped game data. Add `local/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, and `*.egg-info/` exclusions when scaffolding.

## Verification contract

Task 1 establishes these commands rather than claiming they already exist. Run in PowerShell from the repository root:

```powershell
py -3 --version
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\python.exe -m pytest tests/unit tests/scenarios -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src/psp_buddy
.\.venv\Scripts\python.exe -m psp_buddy --help
```

Expected: Python meets the version floor; dependency installation succeeds; all local tests pass; lint/type checks return zero; CLI help lists `inspect`, `validate`, and `run`. If installation is unavailable, report verification incomplete. Capture the installed dependency versions in the validation report for reproducibility. No browser server is required.

Live checks use an explicit local config and are excluded from ordinary pytest runs. The test fixture calls `prepare_trial()` before connecting to the emulator; environment flags never bypass backup protection:

```powershell
$env:PSP_BUDDY_LIVE = '1'
$env:PSP_BUDDY_CONFIG = (Resolve-Path local\config.json).Path
.\.venv\Scripts\python.exe -m pytest tests/integration/test_debugger.py -m live -v
```

Run one live module per freshly backed-up trial. Expected results must include actual game postconditions, not merely debugger acknowledgments. Do not launch or modify PPSSPP during plan preparation.

## Task 1: Scaffold and define contracts

**Files:** Create `pyproject.toml`, package entry files, `models.py`, `config.py`, `config.example.json`, `tests/conftest.py`, `tests/unit/test_config.py`, `tests/unit/test_models.py`; modify `.gitignore`.

- [x] Inspect available Python and choose an installed compatible interpreter. Configure setuptools with a `src/` layout, development dependencies, strict mypy, Ruff, and pytest's `live` marker.
- [x] Write tests rejecting slots outside 1–5, retries outside 0–3, a non-loopback debugger endpoint, missing save roots, and overlapping backup/source roots. Run `python -m pytest tests/unit/test_config.py tests/unit/test_models.py -v` using the venv interpreter; observe failure before implementation.
- [x] Define `Policy`, `Unit`, `Weapon`, `Snapshot`, `Action`, `Prediction`, `CheckpointReceipt`, `Handover`, and `GameProfile`. Use stable IDs; integer HP/resources; phase/screen/action enums; explicit optional unknown fields. Snapshots carry sequence, map identity, capture/profile identity and validation status. Never replace unknown values with zero.
- [x] Define service signatures used throughout: `prepare_trial(config) -> BackupReceipt`, async `observe() -> Snapshot`, `parse_policy(text) -> Policy`, `choose_action(snapshot, policy) -> Action`, async `execute(action, before) -> Snapshot`, async `save_checkpoint(snapshot) -> CheckpointReceipt`, async `load_checkpoint(receipt) -> Snapshot`, and `choose_reaction(snapshot, policy, attempt, history) -> Action`. Put shared return types in `models.py`; keep service implementations in their named files.
- [x] Add this behavioral test and implement configuration validation until it passes:

```python
def test_retry_budget_cannot_exceed_user_limit(config_values):
    from psp_buddy.config import RunConfig
    import pytest
    with pytest.raises(ValueError, match="retries"):
        RunConfig.from_dict({**config_values, "max_retries": 4})
```

- [x] Run focused tests and all static checks. Confirm example configuration contains no personal paths or bundled game data. Review contract names before dependent tasks.

## Task 2: Backup gate before any live connection

**Files:** Create `backup.py`, `tests/unit/test_backup.py`; extend `config.py` and live fixtures in `tests/conftest.py`.

- [x] Write tests using temporary directories containing nested BIN, PPST, metadata, thumbnails, and undo files. Assert complete copies, SHA-256 manifest entries, unique preserved trial directories, and a denied trial when a required source is missing or changes during copying.
- [x] Inject filesystem operations to simulate a copy failure and a hash mismatch. Observe failing tests with `python -m pytest tests/unit/test_backup.py -v`.
- [x] Implement fresh trial directories with separate immutable snapshot and writable trial areas. Inventory and hash sources before/after copying; compare copied bytes; reject overlapping roots, unsafe links, or source instability. Confirm emulator closed or an explicitly validated non-writing condition before copying. Merely checking a stable modification time does not prove non-writing.
- [x] Write the manifest only after successful verification; issue a `BackupReceipt` bound to that trial's roots and inventory. A live adapter must require a current receipt; do not cache authorization across separate trials.
- [ ] Test the guard at the connection boundary:

```python
def test_hash_mismatch_blocks_trial(backup_service, corrupt_copy):
    import pytest
    with pytest.raises(ValueError, match="hash"):
        backup_service.prepare_trial()
    assert backup_service.connection_attempts == 0
```

- [x] Rerun local tests and check that no test reads real saves. Review preservation and manifest correctness before enabling Task 3 live work.

## Task 3: Safe debugger adapter

**Files:** Create `debugger.py`, `launch.py`, `tests/unit/test_debugger.py`, `tests/unit/test_transport.py`, `tests/unit/test_launch.py`, `tests/integration/test_debugger.py`.

Continuation on 11 October: complete the launch boundary before connecting. The launcher creates a fresh four-root backup and complete configuration snapshot, builds an isolated copied executable/assets and writable memory stick, consumes the verified receipt before launch, and binds the actual process and listening socket to a single-use connection session. The WebSocket transport disables proxies, negotiates PPSSPP's debugger subprotocol, normalizes disconnects, and verifies emulator/game identity before exposing input. Synthetic launch/transport tests must fail meaningfully before implementation and pass with Ruff/mypy before a protected runtime trial. These helpers implement the already approved backup/adapter boundary; autonomous `run` remains disabled.

- [x] Test a fake WebSocket delivering unrelated events, mismatched tickets, error replies, and asynchronous pause/resume events. Test deadlines, disconnects, command allowlisting, and no memory-write command transmission.
- [x] Observe red with `python -m pytest tests/unit/test_debugger.py -v`; implement ticket correlation, unsolicited-event routing, bounded memory reads, status, short button presses, and explicit release cleanup. Record command schemas from the tested emulator's API instead of guessing them.
- [x] Test cleanup as an observable safety behavior:

```python
async def test_observation_exception_resumes_running_game(adapter, transport):
    import pytest
    with pytest.raises(RuntimeError):
        async with adapter.observation_pause():
            raise RuntimeError("decode failed")
    assert transport.paused is False
    assert transport.buttons_down == set()
```

- [x] Preserve an existing user pause; resume only a pause this adapter introduced. On uncertain disconnect, report pause status unknown and stop issuing actions.
- [x] After a fresh backup, verify game/version identity and a single bounded cursor input with observed displacement and release. Resume/release in cleanup. Log the tested schemas privately and summarize evidence in research documentation.
- [x] Gate: direct input outcome and cleanup are verified in the actual game. Any failure blocks menu automation, while pure tests may continue.

## Task 4: Capture and game observation discovery

### Capture continuation (2026-10-11, approved next step)

Implement `src/psp_buddy/capture.py` and `tests/unit/test_capture.py`. Add Pillow to `pyproject.toml` for full JPEG/PNG decoding; never accept a header alone. `ScreenshotCapture(session, expected_size)` binds an issuer-created `LaunchSession`. `await capture.capture(trigger, timeout_seconds=...)` inventories the owned `memstick/PSP/SCREENSHOT` directory before awaiting a trigger callback, then accepts exactly one newly named game-ID screenshot within the deadline. The trigger is supplied by the supported Windows computer-use integration; this module does not invent a second Windows input mechanism. Return an immutable frame containing image bytes, digest, sequence, size, game identity and trial identity. Identical image bytes on separate requests are allowed because the game can be stationary; a prior filename, ambiguous output, overwritten baseline, unsafe file/link, changed process binding, blank frame, wrong dimensions, unsupported format or incomplete decode cannot become a frame. Serialize requests and reject reuse after timeout/uncertain failure so delayed output cannot satisfy a later request. Bound file size and read consistency; hold no battle inputs or pause changes.

- [x] Write a failing test using an actual synthetic JPEG/PNG and fake owned launch fixtures: no new file times out; new complete frame is accepted; reused/overwritten/ambiguous files are rejected; partial writes wait until complete; blank/wrong-size/unsafe frames reject; cancellation/trigger failure disables further requests; changed process binding blocks acceptance; two successive identical-content captures remain distinct sequences.
- [x] Run `.\.venv\Scripts\python.exe -m pytest tests/unit/test_capture.py --basetemp=local/pytest-capture-red -v`; observe expected feature-missing failure before writing capture production code.
- [x] Implement the bounded file collector and decoder with no filesystem writes except PPSSPP's own screenshot output. Unit tests must use temporary synthetic saves/files only.
- [x] Run full unit suite with a unique local basetemp, `python -m ruff check src tests`, `python -m mypy src`, CLI help and `git diff --check`. Expected: all checks pass. Run independent working-tree review; fix blocking findings and rerun affected checks.
- [x] Root-owned ignored trial helper uses the existing protected launcher, initializes a capture request before printing readiness, and supplies a marker-wait trigger callback. Root invokes the already-observed Debug → Take screenshot menu through `node_repl` + `sky`, then releases the marker. This validates the collector's live API; it is not an unattended CLI control bridge. Capture two frames, preserve evidence, close owned PPSSPP promptly and verify original/snapshot/archive hashes. Every live invocation gets fresh complete save/configuration backups first.
- [x] Record success/failure and outstanding native trigger/recognition gates. No commit, battle action, guessed memory decoding or autonomous `run` enablement.

**Files:** Create `capture.py`, `recognition.py`, `profile.py`, `reader.py`, `tests/unit/test_reader.py`, `tests/unit/test_recognition.py`, `tests/integration/test_capture.py`, `tests/integration/test_reader.py`, `docs/research/2026-10-10-profile-validation.md`.

#### Bounded stat-reader continuation (2026-10-11)

Fresh Unit/Pilot/Mech screenshots corroborate Gundam 00 HP/max HP 5000/5000, EN/max EN 121/210, defense 1150, mobility 165 and accuracy 170 against the candidate record. Build `profile.py` and `reader.py` with `tests/unit/test_reader.py` for inspection only. `FieldBinding(name, offset, width, evidence_ids)` binds a supported unsigned little-endian stat to nonempty evidence references; `InspectionProfile` carries game/patch/emulator identity, a named unit label, record address/size and explicit bindings. `decode_inspection(profile, data, game_id, patch_id, emulator_version)` returns a frozen stat inspection. Require corroborated current and maximum HP; unknown maximum HP, invalid bounds, duplicate/overlapping bindings, incomplete evidence, identity mismatch, short data, HP above max or EN above max must reject. Optional unvalidated fields remain absent. A valid stat inspection is never an active-roster or tactical snapshot and does not establish map identity, affiliation, coordinates, legal actions or predictions. No production profile may infer those values from the sparse unit/form table.

- Write and observe meaningful failing synthetic decoder tests; implement only the inspection contracts and checked decoding.
- Run all unit tests, Ruff, strict mypy, CLI help and diff checks; review the new untracked files independently and resolve blocking findings.
- Run the decoder against the preserved live record bytes with an explicitly documented Gundam 00 evidence profile. This is offline evidence verification, not a new emulator trial. Record limitations and retain fail-closed autonomous CLI behavior.

- [ ] Create synthetic memory layouts and screen fixtures. Test invalid HP/max HP, unknown affiliation, invalid coordinates, stale sequences, mixed phases, unexpected screens, and game/profile mismatch. Observe red with `python -m pytest tests/unit/test_reader.py tests/unit/test_recognition.py -v`.
- [ ] Before production menu recognition, investigate the failing v1.20.4 capture path in a protected trial. Evaluate debugger capture and a supported Windows capture path; if renderer configuration must change, back it up first and verify copied saves afterward. Keep only a method producing current, nonblank, correctly sized game frames. Document failure if neither works.
- [ ] Validate fields against visible game screens: roster identity/stride, affiliation, coordinates, current/max HP, EN, pilot stats/SP, available actions, Repair/Trust, weapon costs/ranges/legal targets, previews, phases, confirmed defeat, scripted departure, and map clear. Each evidence row names address/layout, units/screens, reload checks, confidence and limitations.
- [ ] Start with recorded candidates `0x08E93A7C = 5000` and `0x08E9235C = 4616`. Confirm max HP separately; do not promote candidate max HP 5300 to validated data without evidence. Check multiple units, different phases and reloads; detect unsupported maps rather than assuming fixed records.
- [ ] Implement decoding only for validated layouts; use bulk debugger reads and a coherent pause or sequence check. Validate profile against game/patch identity and runtime sentinels. Return unavailable capability when required fields lack evidence.
- [ ] Add this fail-closed test:

```python
def test_unknown_max_hp_blocks_tactics(reader, memory_with_unknown_max):
    import pytest
    with pytest.raises(ValueError, match="maximum HP"):
        reader.decode(memory_with_unknown_max)
```

- [ ] Gate: reliable capture plus all fields needed by enabled actions are validated. Damage estimates need visible prediction correlation accounting for defense/modifiers; otherwise disable decisions requiring estimates. No autonomous combat before this gate.

## Task 5: Explicit policy and local tactical rules

**Files:** Create `policy.py`, `planner.py`, `tests/unit/test_policy.py`, `tests/unit/test_planner.py`.

- [x] Parse documented natural-language clauses into explicit bounded settings; reject unmatched nontrivial clauses, contradictions, unsupported tactics and retry limits above three. Display interpreted policy without starting play. Test each supported clause and rejection with `python -m pytest tests/unit/test_policy.py -v` before implementing.
- [x] Add synthetic planner tests for 69/70% healing, reachable repairer reservation, Trust eligibility/SP, post-heal observation, retreat without attack, and no safe improving move. Test all legal action/resource constraints and remaining allies before end-turn.
- [x] Test damaged-before-nearest targeting; finishability within each damage group; lower HP percentage and stable tie-breaks. Test more-than-three type counts, baseline medians, both-stat boss qualification, conflicting/no-baseline fallback.
- [x] Test weapon boundaries below/exact 20%, above/exact 90%, lower median, one/no weapon, zero resources, normalized EN/ammo costs and exclusion of allied-damage/MAP attacks. Observe red with `python -m pytest tests/unit/test_planner.py -v`.
- [x] Example acceptance assertion, using synthetic fixtures from `conftest.py`:

```python
def test_damaged_enemy_precedes_nearer_full_health(planner, battle, policy):
    action = planner.choose_action(battle, policy)
    assert action.target_id == "damaged-far"
    assert action.kind.name == "ATTACK"
```

- [x] Implement pure planning with resource/action reservations; replan from new observations after every executed action. Do not reuse stale reachability or reserve the same healer action twice. Run all rule tests and static checks; this task can proceed independently of unresolved live gates after Task 1 contracts are fixed.

## Task 6: Verified single-slot checkpoints

**Files:** Create `checkpoint.py`, `tests/unit/test_checkpoint.py`, `tests/integration/test_checkpoint.py`.

- [ ] Test wrong slot/game, timeout, partial file, save failure, defeat-before-save, and failed restore. Assert end-turn is prohibited without a valid receipt. Observe red with `python -m pytest tests/unit/test_checkpoint.py -v`.
- [ ] Investigate existing PPSSPP save/load controls on copied saves after a fresh backup. Prefer an available documented debugger mechanism; otherwise verify emulator hotkeys/menu control through a supported adapter. Do not mistake PSP controller input for host save-state control.
- [ ] Verify selected slot 2 explicitly, completion, readable state metadata/game identity and restored snapshot identity. Correlate emulator completion with file integrity and game observation; changed mtime or API acknowledgment alone is insufficient. Preserve prior verified state through supported undo behavior and immutable backups; never rewrite BIN saves.
- [ ] Test the ordering invariant:

```python
async def test_save_failure_prevents_end_turn(supervisor, failing_checkpoint):
    result = await supervisor.finish_player_turn()
    assert result.reason == "checkpoint_save_failed"
    assert "END_TURN" not in supervisor.executor.executed_kinds
```

- [ ] Live gate: mutate only the portable working slot, save a known harmless state, alter cursor, reload and verify restoration and source hashes. Record tested save mechanism and recovery behavior. Failed live validation blocks autonomous runs.

## Task 7: Bounded menu action executor

**Files:** Create `executor.py`, `tests/unit/test_executor.py`, `tests/integration/test_executor.py`.

- [ ] Test transition graphs for move/attack, Repair, Trust, wait, end-turn, and enemy reactions using fake observations. Unknown prompts, stale action IDs, invalid targets, no progress, and user stop must release buttons and return handover without blind retries.
- [ ] Observe red with `python -m pytest tests/unit/test_executor.py -v`. Implement each action as expected screen -> bounded input -> new validated snapshot -> postcondition. Consume resources/actions only through observed game outcomes.
- [ ] Test dialogue handling:

```python
async def test_route_choice_never_receives_skip_input(executor, route_choice):
    result = await executor.handle_dialogue(route_choice)
    assert result.reason == "unexpected_choice"
    assert executor.transport.sent_buttons == []
```

- [ ] Skip only positively recognized decision-free dialogue; never skip deployment, route, or map-clear choices. Limit transitions and repeated identical snapshots per action; unknown outcome terminates that action.
- [ ] After Tasks 3, 4 and 6 gates, verify each enabled menu action on isolated copied saves with fresh backups per trial. Restore the working checkpoint only through verified controls. Unsupported actions remain disabled and block runs that need them.

## Task 8: Enemy reactions and supervision

**Files:** Create `reactions.py`, `supervisor.py`, `tests/unit/test_reactions.py`, `tests/unit/test_supervisor.py`, `tests/scenarios/test_battle.py`.

- [ ] Test defense priority above 80% even below 50% HP; exactly 80% and 50% boundaries; legal counterattack fallback; bounded defense-heavy, evasion-heavy and mixed alternatives. History keys include ally, attacker, weapon/attack context and occurrence so repeated attacks are distinguishable.
- [ ] Observe red with `python -m pytest tests/unit/test_reactions.py tests/unit/test_supervisor.py -v`. Implement states `STARTUP`, `PLAYER_PHASE`, `CHECKPOINT_SAVE`, `ENEMY_PHASE`, `RELOAD`, `HANDOVER`. Retry count lives outside emulator state; increment only on successful reload, reset only after a successful enemy phase.
- [ ] Add a four-failure scenario:

```python
async def test_initial_plus_three_failures_stops(runner, four_failed_attempts):
    result = await runner.run(four_failed_attempts)
    assert result.reason == "retry_limit"
    assert result.retry_count == 3
    assert runner.checkpoints.reload_count == 3
    assert runner.checkpoints.saved_defeated_state is False
```

- [ ] Test no distinct alternatives -> early handover; scripted departure -> no defeat reload; map clear -> no next-map inputs; backup/save/load/connection failure -> stop; Ctrl+C -> cleanup and concise report. Retry may change reactions only, never reissue allied movement/healing from the saved checkpoint.
- [ ] Add a simulated multi-turn scenario proving one slot, save-before-end-turn, successful-phase budget reset, bounded action count, no resource overspending and no runtime network/model calls beyond local debugger traffic.
- [ ] Rerun the complete offline suite. Review state transitions and acceptance coverage before CLI live execution.

## Task 9: CLI, dry-run report and user instructions

**Files:** Create `cli.py`, `docs/usage.md`; extend `__main__.py`, `config.example.json`, `README.md`, `tests/unit/test_cli.py`.

- [ ] Test `--help`, bad configuration/policy, unavailable gates, read-only inspection and dry-run planning. A command called dry-run must never save or send battle inputs; live observation still requires the backup gate.
- [ ] Observe red with `python -m pytest tests/unit/test_cli.py -v`; implement `inspect --config`, `validate --config`, and `run --config --instructions-file`. Configuration names original/portable roots, executable/ISO paths, profile, local endpoint, slot and run budgets. Instructions files stay local.
- [ ] `validate` produces a capability report. `run` refuses unmet gates, displays parsed policy, requires the configured reviewed policy identity, and records a local session ID. Implement terminal stop via Ctrl+C and document manual PPSSPP resume controls validated for that installation.
- [ ] Handover reports reason, checkpoint receipt/slot, retry count, affected allies, recent action history and known pause state. Explain recovery from portable checkpoints or immutable backup without automatically changing original saves.
- [ ] Run all verification commands. Inspect tracked/untracked public files for paths, game assets and private evidence; use `git check-ignore` to prove exclusion of representative backup, BIN, PPST, ISO and local configuration paths.

## Task 10: Protected battle acceptance and final review

**Files:** Update `docs/research/2026-10-10-profile-validation.md`, `docs/usage.md`, `README.md`, this plan's checkboxes; private evidence under the new trial directory.

- [ ] Run offline tests, Ruff, mypy and CLI help. All must pass before final code review. Record exact results and dependency versions.
- [ ] Confirm Tasks 3/4/6/7 live gates passed. Create a fresh verified backup; verify the effective portable memory stick and selected state. Present effective policy and run the one-map trial only within already authorized implementation/test scope.
- [ ] Verify healing/retreat, damaged-target selection, weapons, enemy responses, same-slot save before end-turn, safe dialogue and map-clear handover. Do not manufacture defeat by writing RAM or spending user retries merely to collect evidence. Synthetic scenarios cover exhausted retries; label any live behavior not encountered as unverified.
- [ ] Stop immediately for uncertain observation or state changes. Hash-check original saves afterward, preserve evidence and clearly distinguish successful gates from incomplete battle acceptance.
- [ ] Use the available code-review skill on the complete working tree after checks pass. Inspect `git diff HEAD` and `git status --short`, and read intended untracked text files because the diff omits them. Exclude private backup data from review output.
- [ ] Fix Critical/Important findings; rerun affected checks and review again. Report Minor findings and incomplete live coverage. Capture the final game screen only through the validated capture method.
- [ ] Hand over change summary, test/review results, research evidence, limitations and resume instructions. Leave everything uncommitted.

## Scheduling and review boundaries

Execute Tasks 1–4 sequentially for contract and integration discovery. After Task 1, Task 5 can be assigned to a bounded policy/planner subagent while the primary agent handles protected discovery; it writes only its listed modules/tests. Checkpoint and executor live work remain sequential to avoid competing emulator control. Task 8 follows reviewed planner/executor/checkpoint contracts; Tasks 9–10 follow reviewed safety behavior. Do not delegate simultaneous emulator trials.

These are stages of one safety-dependent MVP, rather than independent products. Offline policy/supervisor work yields useful tested code even if integration is blocked; it does not authorize declaring an autonomous runner complete.

## Spec coverage and plan self-review

### Task 3 continuation: fixed MVP runtime (user selected 2026-10-11)

- Add optional `runtime_root` to `src/psp_buddy/launch.py`; keep default isolated trials unchanged. Use `local/runtime/ppsspp-v1.20.4/app` for the manual capture trial.
- In `tests/unit/test_launch.py`, observe failing tests for stable executable/state paths, reuse of backed-up test saves, preservation of prior runtime contents, rejection of unowned/mismatched roots, and unchanged originals.
- Preserve complete verified backups/configuration and uniquely archive the owned prior runtime; never overwrite or delete earlier evidence. Post-trial verification distinguishes mutable active test roots from immutable originals and snapshots.
- Run unit tests, Ruff, strict mypy, and independent working-tree review before launching. Then perform one fresh protected live trial and use PPSSPP's observed Debugging → Take Screenshot menu. Inspect any resulting image, close the owned emulator, and verify preservation checks. A capture failure leaves the observation gate incomplete.

Continuation evidence: fixed-path reuse launched successfully after fresh backups without a repeated firewall alert. Two newly created, visually inspected JPEGs from the observed Debug → Take screenshot command show nonblank game maps. Keyboard menu navigation worked despite indexed-click geometry failure. See the research checkpoint for trial paths and hashes. Automated file-capture integration, cursor displacement and complete recognition remain outstanding; no autonomous battle was run.

| Spec requirement | Tasks/evidence |
| --- | --- |
| One map, start/configure, local natural language, public hygiene | 1, 5, 9, 10 |
| Original and portable backups, verification, no automatic copying back | 2 and every live fixture |
| Reliable capture, coherent complete observations, candidate HP validation | 3, 4 |
| Healing, reservations, retreat, targets, boss heuristic, weapon rules | 5, 7 |
| Initial defense priority and legal reactions, overriding retry strategies | 8 |
| One slot, save before end-turn, successful load verification | 6, 8 |
| Three retries, outside-state counter, success reset, early stop | 8 scenarios |
| Map clear, unknown prompts, disappearance/defeat distinction, stop/cleanup | 4, 7, 8, 9 |
| No runtime LLM, TDD, actual-app verification, code review | 5, 8, 10 |

Self-review: all approved requirements map to tasks; service names and return types are consistent; no existing verification setup is assumed. Remaining uncertainty is explicitly assigned to live evidence gates. No production code or emulator trial was performed while preparing this plan.

### Task 4 continuation: bounded stat inspection (2026-10-11)

- Add `profile.py` and `reader.py` with immutable evidence-bound field layouts and inspection results, exact game/patch/emulator identity checks, bounded little-endian decoding, and rejection of inconsistent HP/EN/SP. Require corroborated current and maximum HP; leave unknown optional stats absent. Do not infer roster or tactical state.
- Observe meaningful failing tests in `tests/unit/test_reader.py`, implement, then run the full offline suite, Ruff and strict mypy. Independently review before proceeding to dependent game-state work.
- Verify the decoder offline against the protected trial's preserved Gundam 00 record and visible mech screen. No emulator launch is needed for this verification.

Implementation checkpoint: 28 reader tests and all 234 offline tests pass; Ruff and strict mypy pass. The preserved record decodes HP 5000/5000 and EN 121/210, matching the visible screen and the user's HP interpretation. Full roster and tactical observation gates remain incomplete.
