# PSP Buddy development usage

Implementation is in progress. The package and local tactical rules can be tested without PPSSPP. `validate` reports offline configuration/profile capabilities; `inspect --record` decodes supplied record bytes. `run` refuses live execution, including with `--dry-run`; no autonomous battle capability has been validated.

## Setup and offline checks

From the repository root in PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
$testRunId = Get-Date -Format 'yyyyMMdd-HHmmss-ffff'
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp "local/pytest-$testRunId"
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src/psp_buddy
.\.venv\Scripts\python.exe -m psp_buddy --help
```

Python 3.11 or newer is required. Tests use synthetic observations and temporary save trees. Ordinary test runs exclude live tests. On this Windows installation, the sandbox blocks access to Python-created temporary directories; synthetic pytest checks were verified with approved execution outside that restriction.

Copy `config.example.json` to ignored `local/config.json` and supply your own paths. Relative paths are resolved against the configuration file's directory: after copying, adjust them accordingly (for example, `profile.json` and `../backups`). Existing save directories, distinct original/portable roots, a separate backup root, and a loopback WebSocket endpoint are required. A structurally valid configuration does not establish a validated game profile or authorize play. Do not put backups inside any source save directory or source directories inside the configured backup root.

## Read-only CLI commands

```powershell
.\.venv\Scripts\python.exe -m psp_buddy validate --config local/config.json
.\.venv\Scripts\python.exe -m psp_buddy validate --config local/config.json --instructions-file local/instructions.txt
.\.venv\Scripts\python.exe -m psp_buddy inspect --config local/config.json --record local/record.bin
.\.venv\Scripts\python.exe -m psp_buddy run --config local/config.json
```

Successful `validate` and `inspect` commands print JSON and exit with code 0. Invalid input and disabled `run` exit with code 2. `validate` checks the configuration schema, local save roots, inspection-profile identity and optional policy clauses. It reports each live gate as unestablished by this offline command. The report does not certify executable/game-image contents or authenticate the profile's evidence references. A configured retry ceiling can reduce the default policy; instructions requesting more retries than that ceiling are rejected.

`inspect` requires `--record` containing exactly the profile's `record_size` bytes. Omitting it cannot fall back to live memory observation. Output includes decoded values, supplied provenance, `live_authenticated: false`, and `tactical_snapshot_available: false`. Neither command imports live control adapters or writes saves. `--dry-run` is accepted for `validate` and `run`; validation is always read-only, and the flag cannot bypass `run`'s live gates.

The configured profile file accepts only `kind: "stat_inspection"`, `schema_version: 1`, exact game/patch/emulator identity, a unit label, bounded record address/size, and field bindings. Each field needs a supported name, offset, width (1, 2 or 4 bytes), and nonempty evidence references. Duplicate JSON keys, unknown descriptor fields, overlapping bindings and unsupported tactical-profile claims are rejected. This example illustrates the schema only; its offsets/address are not a calibrated game profile:

```json
{
  "kind": "stat_inspection",
  "schema_version": 1,
  "game_id": "ULJS00460",
  "patch_id": "english-v0.8",
  "emulator_version": "1.20.4",
  "unit_label": "Supplied inspection fixture",
  "record_address": 142606336,
  "record_size": 4,
  "fields": [
    {"name": "hp", "offset": 0, "width": 2, "evidence_ids": ["supplied-hp-reference"]},
    {"name": "max_hp", "offset": 2, "width": 2, "evidence_ids": ["supplied-max-hp-reference"]}
  ]
}
```

The offline CLI currently loads robot-style `InspectionProfile` descriptors. The separate `PilotInspectionProfile` API below does not yet have a CLI descriptor format.

## Supported local instructions

The bounded parser accepts these clauses, separated by semicolons or newlines. Percentages are whole numbers from 0 through 100; retries are from 0 through 3. Different values for the same setting are rejected. Unsupported clauses are rejected in full.

```text
heal below 70%; evade below 50%; defend above 80% hit rate
cheap weapons below 20%; strongest boss weapons above 90%
common types have more than 3 instances; retry at most 3 times
prefer repair then trust then retreat
target damaged enemies before undamaged enemies
use medium strength weapons otherwise; stop on map clear
```

An empty instruction string selects the specification's defaults. Rules run locally, without model calls. The planner returns one action tied to the current validated snapshot. The caller must execute and reobserve before choosing again. Unknown required resources, legal actions, predictions, or enemy attack coverage produce handover rather than invented values.

## Protection and remaining gates

Before every live trial, both complete original save directories and both active portable save directories must receive a fresh verified snapshot. Earlier backups are preserved. Verified snapshots and writable trial copies remain separate. Never copy trial saves automatically back to the original memory stick.

Live debugger transport, reliable capture, complete game-state decoding, checkpoint save/load, menu execution, and the supervisor must be verified before `run` is enabled. A debugger acknowledgement alone does not prove the intended game outcome. The implementation plan records these gates and progress; passing offline tests does not imply successful autonomous play.

The protected launch, runtime identity connection and screenshot collection API have been exercised. PPSSPP's built-in Debug → Take screenshot command produced validated game images in fixed-path trials, and one short cursor movement was visually verified. Windows screen capture and debugger GPU capture remain unsuccessful; complete recognition and battle execution remain gated. The observation-only integration test requires explicit opt-in, a local configuration and the exact selected state filename. Every invocation creates a fresh verified backup and configuration snapshot, uses an isolated copied application/memory stick, closes its owned process, and checks source hashes afterward:

```powershell
$env:PSP_BUDDY_LIVE = '1'
$env:PSP_BUDDY_CONFIG = (Resolve-Path local\config.json).Path
$env:PSP_BUDDY_STATE = 'ULJS00460_1.01_1.ppst' # slot 2 for this approved game/version
.\.venv\Scripts\python.exe -m pytest tests/integration/test_debugger.py -m live -v
```

Keep PPSSPP closed before starting. This test verifies identity and pause cleanup; it does not send battle inputs or prove cursor movement. Debugger transport requires an owned launch session; an arbitrary endpoint cannot enable it.

Changes remain uncommitted unless the user explicitly requests a commit. Backups, local configuration, raw frames, logs, game images, and save files are excluded from Git.

For MVP capture testing, `Launcher.prepare(..., runtime_root=Path("local/runtime/ppsspp-v1.20.4"))` keeps the executable at `local/runtime/ppsspp-v1.20.4/app/PPSSPPWindows64.exe` and state under `app/memstick/PSP/PPSSPP_STATE`. On the first trial, use the canonical portable bundle as the source. On later trials, the configured portable save roots and SYSTEM source must identify the active fixed memory stick. Each trial creates fresh verified backups and preserves the complete previous owned runtime in a unique sibling archive before rebuilding. Active test saves may change; originals and preserved evidence must remain unchanged. Unknown runtime contents fail closed. This option is currently a protected launch API for testing, not an enabled autonomous CLI flow.

A Windows firewall approval applies to a particular executable path. Keeping this path fixed should avoid prompts caused by a new trial path each time, although Windows policy or updates may still require approval. Firewall access and screen capture are separate permissions. Handle Windows security prompts yourself; this project does not alter firewall settings.

## Screenshot collection API

`ScreenshotCapture(session, expected_size=(944, 541))` binds to a protected owned launch. `await collector.capture(trigger, timeout_seconds=120)` records existing screenshot files, awaits the supplied async menu trigger, then accepts one newly named game screenshot only after stable reads and complete JPEG/PNG decoding. The observed size is specific to the current test configuration. The returned immutable `CapturedFrame` includes encoded bytes, SHA-256, sequence, size, game ID and trial ID. Use its bytes rather than reopening a mutable source file.

The collector rejects blank/wrong-size images, changed baseline files, ambiguous output, unsafe links and changed process ownership. A timeout, cancellation or trigger failure makes completion uncertain and disables further requests on that collector. Identical bytes in separately created files are allowed when the game is stationary. The caller must supply the supported Windows menu integration; this API does not itself inject native input or enable unattended CLI execution. A protected live trial verified one short right cursor movement and acknowledged release against before/after captures. Complete recognition, other menu flows and unattended execution remain separate gates.

Images are fully decoded with [Pillow's image-loading API](https://pillow.readthedocs.io/en/stable/reference/Image.html), rather than accepting file headers as proof of completeness.

## Bounded stat inspection API

`InspectionProfile` describes an explicitly corroborated record using immutable `FieldBinding` entries with evidence references. `decode_inspection(profile, record_bytes, game_id, patch_id, emulator_version)` checks the identities and decodes bounded unsigned little-endian fields. Current and maximum HP are required; overlapping fields, incomplete records and resource values above their supplied maxima are rejected. Missing optional stats remain unavailable through `StatInspection.get(name)`.

The preserved Gundam 00 record matches its visible HP `5000/5000`, EN `121/210`, defense 1150, mobility 165 and accuracy 170. This API does not read emulator memory itself or produce a tactical snapshot. Evidence references are caller-supplied provenance, not automatically authenticated files. Deployed roster, affiliation, coordinates and legal actions still need validation before autonomous play.

`PilotInspectionProfile` describes a separate named pilot-record window with evidence-bound `sp`, `level`, and optional `max_sp`/`will` bindings. `decode_pilot_inspection(profile, record_bytes, game_id, patch_id, emulator_version)` requires exact-sized immutable bytes, matching identity and a positive level, and rejects SP above a supplied maximum. Its `PilotInspection` result carries a pilot label and record-window label, without claiming a deployed pilot identity, roster membership or tactical state. The reader passed independent review. Preserved fresh samples from two protected launches decode Setsuna SP `55/95`, level 36 and will 150, matching visually inspected screens. This corroborates one stationary named fixture; other pilots, record strides and cross-map identity remain unvalidated.

The offline inspection and control contracts below do not enable autonomous CLI execution.

## Conservative screen recognition

`signature_from_frame(frame, label, screen, boxes, evidence_ids)` builds an immutable signature
from at least two nonoverlapping, nonuniform landmarks. `ScreenRecognizer(game_id, trial_id,
size, signatures)` consumes only intact matching-identity frames with increasing sequences.
Every landmark must meet the conservative pixel-error threshold; unknown and ambiguous
screens return `Screen.UNKNOWN`. The result carries the frame digest, sequence and evidence
references, with no decoded text, phase, unit identity, or legal-action claims.

Private calibration distinguishes the preserved Unit/Pilot/Mech information screens and
rejects the preserved map and command menus. Static anchors have been recalibrated to avoid
changing stat content. The unchanged frozen profile correctly classified Unit/Pilot/Mech
and rejected map/command screens in a separate protected launch of the same fixture.
Other units, layouts and battle prompts remain unvalidated. Changed rendering or
layout may still produce unknown results. Evidence references are caller-supplied provenance;
signature selection must be separately reviewed before use. These signatures identify screen
classes, not the active menu choice or tactical state. Production screen/menu profiles remain
a live gate.

## Offline checkpoints and supervision

`VerifiedCheckpointService(slot, game_id, map_id, backend, state_root=...)` binds one user-facing
slot (1–5), reads only within the configured protected state root, and caps artifacts at
128 MiB. `verify_initial_checkpoint(snapshot, state_path)` adopts a selected existing state
without issuing save/load commands. Save/load receipts require correlated completion,
complete decoded artifact metadata, SHA-256 integrity, a matching tactical-state fingerprint,
and fresh matching observation. The backend must establish these from real emulator/state
evidence; no live backend or PPSSPP state decoder is implemented. A fingerprint is an
in-process comparison contract, not a field in a PPSSPP state header.

`current_snapshot` returns the last checkpoint observation. `can_end_turn` accepts only the
current issuer receipt and that observed state after completed allied actions. On uncertain
completion, the previous receipt remains available for handover, while further operations
are disabled. This does not prove that the prior on-disk state survived a failed save; supported
undo/recovery behavior still needs protected validation. Synchronous filesystem operations
cannot be preempted; bounded reads and explicit deadline checks fail closed when they return.

`BattleSupervisor` composes trusted injected observers, executors and checkpoint services with
the existing pure planners. It verifies startup, saves before ending a player turn, counts a
retry only after successful fresh restoration, and prevents replay of allied actions during
enemy-phase retries. A successful enemy phase resets the budget; four failed attempts exhaust
the default initial-plus-three-retries allowance. Unknown choices/state, missing allies without
departure/defeat evidence, no progress, timeouts, budgets and user stop cause handover.

Reaction inputs require `IncomingAttack` evidence tied to the observation, checkpoint and attack
occurrence. Retry estimates are validated survival scores, not guarantees. Failed reactions
are recorded by contextual attack identity. Consecutive attacks can advance without changing
HP, while repeated unchanged occurrence evidence does not establish progress. Decision-free
dialogue additionally requires a reviewed `Snapshot.dialogue_id` identifying its content or
script position; an increasing frame sequence alone cannot justify another skip.

## Bounded executor API

`BoundedExecutor(adapter, recipes, stop_requested=..., max_steps=16,
timeout_seconds=5, cleanup_timeout_seconds=2)` implements the generic transition engine.
The recipe provider receives the exact action and source snapshot and returns an immutable
`ActionRecipe`, or `None` to refuse an unsupported action. Recipes bind the source capture,
sequence and game/patch/map/profile identity using `RecipeBinding.from_snapshot(snapshot)`.
Each `RecipeStep` supplies a finite adapter command, expected before/after contexts,
reviewed evidence references and an explicit postcondition. A separate final postcondition
must confirm the action outcome. There are no default production menu sequences.

The injected adapter implements `observe() -> ExecutionObservation`, `send(command)` and
`release_all() -> bool | None`. Observations include the validated snapshot, reviewed menu
identity, `ActionSelection`, and dialogue/attack context when applicable.
`ExpectedContext.from_observation(observation)` creates an exact context expectation.
Before sending, the executor reobserves fresh unchanged tactical evidence and current legal
action membership. It verifies each transition and rejects choices, unexpected menus,
stale selections, unexplained allied disappearance, missing dialogue/attack evidence and
no progress. Positively recognized decision-free dialogue requires a changing dialogue
identity or leaving that screen; a fresh capture alone is insufficient.

`execute(action, before) -> Snapshot` returns only after final postconditions and control
release. Verified final defeat and map-clear outcomes are returned to the supervisor for
reload or handover; they never authorize another intermediate input. Uncertain outcomes
raise `ExecutionError` with a handover reason and disable that executor. Stop, timeout,
connection loss and cancellation attempt bounded release; repeated cancellation cannot
abandon awaiting that release. `cleanup()` returns known pause status or `None`, without
toggling pause. Cleanup failure is reported explicitly.

Recipes, predicates and adapter evidence require separate review and live calibration.
Synchronous adapters/predicates cannot be preempted; explicit elapsed-deadline checks apply
when they return. No live menu adapter, calibrated production recipes, live checkpoint
backend, or autonomous runner is available.

The synthetic two-turn scenario composes the actual bounded executor, checkpoint, tactical,
reaction and supervisor services with an offline world. It verifies one working slot, save-before-end-turn,
reaction-only retry, successful-phase reset and map-clear handover. It does not validate game
menus or actual PPSSPP state parsing. Supported Windows menu control is available in the
13 October session, while capture still requires that caller-supplied control plus the
screenshot collector. A standalone unattended capture bridge remains unimplemented.

Verification on 13 October 2026: 545 offline tests pass, Ruff `check .` and strict mypy `src`
(19 source files) pass. CLI validation/record inspection work offline; `run` refuses live
execution as expected. Current session changes remain uncommitted.
