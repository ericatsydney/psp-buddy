# PSP Buddy development usage

Implementation is in progress. The package and local tactical rules can be tested without PPSSPP. `inspect`, `validate`, and `run` currently refuse execution; no autonomous battle capability has been validated.

## Setup and offline checks

From the repository root in PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\python.exe -m pytest tests/unit -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy src/psp_buddy
.\.venv\Scripts\python.exe -m psp_buddy --help
```

Python 3.11 or newer is required. Tests use synthetic observations and temporary save trees. Ordinary test runs exclude live tests. On this Windows installation, the sandbox blocks access to Python-created temporary directories; synthetic pytest checks were verified with approved execution outside that restriction.

Copy `config.example.json` to ignored `local/config.json` and supply your own paths. Existing save directories, distinct original/portable roots, a separate backup root, and a loopback WebSocket endpoint are required. A structurally valid configuration does not establish a validated game profile or authorize play. Do not put backups inside any source save directory or source directories inside the configured backup root.

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

The preserved Gundam 00 record matches its visible HP `5000/5000`, EN `121/210`, defense 1150, mobility 165 and accuracy 170. This API does not read emulator memory itself or produce a tactical snapshot. Evidence references are caller-supplied provenance, not automatically authenticated files. Pilot SP bindings, deployed roster, affiliation, coordinates and legal actions still need validation before autonomous play.

The reader passed independent review with no Important or Critical findings. The complete offline suite has 234 passing tests, with Ruff and strict mypy also passing.
