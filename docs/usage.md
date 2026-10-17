# PSP Buddy development usage

Implementation is in progress. The package and local tactical rules can be tested without PPSSPP. `validate` reports offline configuration/profile capabilities; `inspect --record` decodes supplied stat bytes; `inspect-map --records` inspects supplied named records with explicit unknown map fields. `run` refuses live execution, including with `--dry-run`; no autonomous battle capability has been validated.

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

For the original commands, the configured profile file accepts only `kind: "stat_inspection"`, `schema_version: 1`, exact game/patch/emulator identity, a unit label, bounded record address/size, and field bindings. Each field needs a supported name, offset, width (1, 2 or 4 bytes), and nonempty evidence references. Duplicate JSON keys, unknown descriptor fields, overlapping bindings and unsupported tactical-profile claims are rejected. This example illustrates the schema only; its offsets/address are not a calibrated game profile:

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

MVP unit commands are Move and Attack only. Repair (healing), all Spirit commands
(including Trust), Supply, Transform and crew changes are excluded. The legacy parser
still accepts the healing clauses above for configuration compatibility; they do not
enable healing. The HP threshold remains the existing retreat threshold. The executor
rejects Repair/Trust even when a caller supplies a legal-action entry and recipe.
Wait/End Turn and enemy reactions remain existing orchestration controls.

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

## Offline named-record map inspection

```powershell
.\.venv\Scripts\python.exe -m psp_buddy inspect-map --config local/map-config.json --records local/map-records.json
```

The config uses the existing machine schema; its `profile_path` points to a separate
`map_inspection` descriptor, schema version 1. Exact descriptor keys are `kind`,
`schema_version`, `game_id`, `patch_id`, `emulator_version`, `map_label`, `dimensions` and
`records`. `dimensions` is null when unknown, or `[width, height]` in 1..1024. Each explicit
record has `label`, `address`, `size`, `fields`; each field has `name`, `offset`, `width`,
`evidence_ids` and `meanings`. Names are unit_id, hp/max_hp, en/max_en, sp/max_sp, x/y,
side and action_available. Ordinary numeric fields use `meanings: []`. Side/action encodings
require explicit `[raw_integer, meaning]` pairs: ally/enemy/neutral or available/spent.
Coordinates require both x/y and known dimensions. HP maxima must be positive; EN/SP may
have zero capacity when current is zero. Layouts and record windows must not overlap.

The separate records manifest contains exact `kind: "map_records"`, `schema_version: 1`
and a `records` array of `{ "label": "matching profile label", "path": "record.bin" }`
entries in profile order. Relative binary paths resolve against the manifest directory.
Supply exact-sized immutable bytes; records are bounded at 64 KiB each, 256 records and
1 MiB total. Duplicate JSON keys, wrong types, unknown keys, mismatched labels/count/order,
identity mismatch and invalid enum/resource/coordinate values fail closed.

Reports always say `named_records_only` and retain missing fields as null plus reasons.
Supplied evidence references are assertions; this command never certifies deployment or
live authentication. Terrain, phase, legal actions and complete deployed roster remain
unavailable. No live control adapters are imported; a missing manifest cannot launch PPSSPP.
The report is suitable for research, not a tactical Snapshot or autonomous play.

The installed local MCP 0.2.0 passed a separate protected live known-record read comparison
with Python on 14 October. The sampled fixture matched HP5000/5000, EN121/210 and SP55/95,
with original/snapshot/archive hashes preserved. Supported capture failed in a separate trial,
so deployed positions and affiliations remain unverified. The project MCP registration stays
disabled outside protected trials. See the [assessment](research/2026-10-14-mcp-ppsspp-assessment.md)
and [map-inspection plan](superpowers/plans/2026-10-14-map-inspection.md).

## Offline structural unit-pool inspection

`inspect-map` also accepts a `unit_pool_inspection` profile (schema version1) and an
`inspection_spans` manifest. This reader enumerates candidate pool slots and retains every
associated robot/pilot descriptor binding. It handles varying candidate counts and preserves
multiple forms/crew without choosing a primary pilot. The existing named-record format is
still available for separately established stat fields.

```powershell
.\.venv\Scripts\python.exe -m psp_buddy inspect-map --config local/pool-config.json --records local/pool-spans.json
```

Use the existing machine-config schema, with `profile_path` pointing to this descriptor.
The following example uses invented addresses and the SHA-256 of four ASCII bytes `ABCD`;
it is a synthetic layout illustration, not a game profile:

```json
{
  "kind": "unit_pool_inspection",
  "schema_version": 1,
  "game_id": "synthetic-game",
  "patch_id": "synthetic-patch",
  "emulator_version": "synthetic-emulator",
  "map_label": "synthetic map",
  "pool_address": 142610432,
  "pool_capacity": 3,
  "pool_stride": 104,
  "actor_owner_address": 142614528,
  "actor_node_array_address": 142622720,
  "actor_stride": 16,
  "actor_capacity": 4,
  "actor_vtable": 142626816,
  "evidence_ids": ["synthetic-layout-v1"],
  "code_anchors": [{
    "address": 142622720,
    "size": 4,
    "sha256": "e12e115acf4552b2568b55e93cbd39394c4ef81c82447fafc997882a02d23677"
  }]
}
```

A matching manifest uses exact keys:

```json
{
  "kind": "inspection_spans",
  "schema_version": 1,
  "spans": [
    {"address": 142610432, "path": "pool.bin"},
    {"address": 142614528, "path": "owner.bin"},
    {"address": 142618624, "path": "actors.bin"},
    {"address": 142622720, "path": "anchor.bin"}
  ]
}
```

Binary files must contain coherent supplied bytes for the declared layout: here pool.bin
is312bytes, owner.bin28bytes, actors.bin64bytes and anchor.bin is `ABCD`. The owner header
supplies the actor-data pointer; it must point to the captured actors window. Required
windows must fit entirely inside one supplied span; gaps, overlap and implicit concatenation
are rejected. Paths resolve relative to the manifest. Limits are32spans,64KiB per span and
1MiB total. Addresses are unsigned integer PSP addresses; pool/actor/owner pointers are
four-byte aligned. All binary fields are unsigned little-endian. Strict keys, identity,
code hashes and alias counts are checked before a report is accepted.

Reports say `candidate_slots_only` with `user_supplied_spans_and_profile` provenance.
They expose raw state words and pixel pairs, sorted actor bindings, ambiguity pointer sets
and exclusion counts. Slot indexes are local to this supplied observation. HP/EN/SP, names,
absolute tiles, sides, phase, dimensions, terrain and legal actions remain undecoded.
Raw state groups are not faction enums. Supplied fingerprints and matching alias counts
cannot authenticate live identity, coherent capture timing or a complete tactical roster.
All live/autonomous capability flags remain false; `run` stays disabled.

This command reads regular local files only. It does not parse .ppst files, scan full RAM,
launch/control PPSSPP or fetch missing bytes. See the
[approved binary and JSON contracts](superpowers/specs/2026-10-16-unit-pool-inspection-design.md).

16 October retained-data geometry verification: private `map_inspection` profiles now use
code-backed direct tile fields and dimensions across three maps (69/12/26 candidate records).
The existing CLI reports coordinates with `named_records_only` provenance and all live/tactical
capabilities false. This does not change the structural unit-pool report or add an automatic
geometry profile. See the [geometry evidence](research/2026-10-16-map-geometry.md) and
[plain-language progress summary](research/2026-10-16-map-evidence-summary.md).

### Current-form representative inspection (offline)

The `representative_inspection` profile kind under `inspect-map` resolves one representative
per structural candidate by reconstructing the source recipe and checking the cached set.
It reports mech/pilot IDs, current/max HP and EN, current SP, DEF, MOB and HIT. It preserves
all existing `map_inspection` and `unit_pool_inspection` behavior; use the structural kind
when you want every alias rather than a selected representative.

```
python -m psp_buddy inspect-map --config local/your-config.json --records local/your-spans.json
```

The configuration's `profile_path` selects a strict version1 `representative_inspection`
JSON descriptor. It contains the unchanged nested `pool_profile`, source/cache/selector/
exclusion global addresses, declared mech/pilot descriptor regions, one or two12-byte-node
regions, evidence references and code-anchor SHA-256 hashes. See the exact field and recipe
contract in `docs/superpowers/specs/2026-10-16-representative-inspection-design.md`; all
addresses/hashes must describe your supplied evidence, not guessed values.

The separate records manifest has this shape (addresses and paths here are synthetic):

```json
{"kind":"representative_spans","schema_version":1,"spans":[
  {"address":142671872,"path":"captured-window.bin"}
]}
```

Relative paths resolve from the manifest directory. Supply1..128regular unlinked binary
files, each at most64KiB and at most1MiB together, with nonoverlapping captured RAM windows.
A partial example alone is insufficient: every descriptor/code/table/record window needed
by the recipe must be present. Unsupported/missing/inconsistent data returns error status2,
with no partial success or live memory fallback. Old manifest kinds retain their old limits.

Output includes a `representatives` array, source/cache/reconstructed counts, supplied-span
hashes and explicit unavailable fields. Names, MV, positions, sides, terrain and legal
actions remain unavailable. Raw SP does not establish how shared crews can spend it.
Slot/object/actor identifiers belong to the observation, not the campaign. Supplied profiles
and hashes do not authenticate live identity or capture timing. All live/tactical/autonomous
capability flags remain false; `run` remains disabled. The MVP has no Transform action;
form changes were used only to corroborate the reader's selected-record semantics.

### Robot tile positions (offline)

Use profile kind `positioned_representative_inspection` to add `tile_x`/`tile_y` to each
selected robot and `dimensions: {width,height}` to the report. Coordinates are zero-based:
X must be less than width and Y less than height. These describe the supplied capture,
not a newly authenticated live emulator state.

The exact descriptor contains `kind`, `schema_version:1`, `representative_profile` (a
complete unchanged representative descriptor) and `geometry`. Geometry contains the
aligned `width_address`/`height_address`,1..16code anchors (`address,size,sha256`) and
`evidence_ids`. See `docs/superpowers/specs/2026-10-16-positioned-inspection-design.md`.
All addresses and fingerprint hashes come from your captured evidence. The existing
`representative_spans` manifest and inspect-map command remain the same. Existing profiles
continue to return their original output; coordinates require the explicit new kind.

Missing/out-of-bounds fields reject the whole report with status2. Captured dimensions
are bounded to1024cells; this inspector does not read a terrain/occupancy grid. Positions
and statistics do not establish reachability, targets, side or action legality. Every
live/tactical/autonomous capability stays false, and no Transform action is added.

### Ally/Foe menu membership (offline)

Use descriptor kind `menu_membership_inspection` under the same `inspect-map --config ...
--records ...` command to extend positioned robot records with menu membership. Output rows
retain form/pilot IDs, stats and tiles, adding `raw_menu_group_byte`, `menu_category_index`
and `menu_membership`: `ally_menu`, `foe_menu`, or `outside_ally_foe_menus`. Counts distinguish
all four categories and the Ally/Foe/outside totals. Wing Zero is outside both observed menus;
this does not label it neutral or nonhostile. Tactical `side` remains unavailable.

The strict version1 descriptor has these exact keys:

- `kind`, `schema_version`, `positioned_profile`: complete unchanged positioned descriptor.
- `menu_mask_table_address`: aligned captured address of four little-endian u32 masks.
- `expected_category_masks`: four nonzero16-bit values, disjoint and covering all16supported
  group bits; captured values must match exactly.
- `ally_category_index`, `foe_category_index`: distinct0..3 indices, explicitly backed by
  your menu-label evidence. They are not inferred from robot counts or UI instance slots.
- `code_anchors`, `evidence_ids`: query/producer fingerprints and bounded evidence references.

For a synthetic mapping, masks `[1,2,4,65528]` partition all16bits; indices0/1 name their
first two categories. Supply your own captured addresses, matching fingerprints and complete
nested profile rather than treating this synthetic example as a game profile. Existing
`representative_spans` limits and file safeguards apply; existing kinds/output remain unchanged.

The decoder fingerprints the expected readonly table and combines it with the query, nested
recipe and geometry fingerprints using the existing32-entry/16KiB budget. Raw group values
outside0..15 are unsupported and reject the report, including values that the underlying
MIPS shift would wrap. Missing/inconsistent evidence returns status2 without partial output,
live fallback or game input. `label_source` explicitly states `user_supplied_menu_label_mapping`;
profile references and counts do not authenticate a live roster. All live/tactical/autonomous
flags stay false. Name decoding, MV, actions, terrain, hostility and diplomatic changes remain
outside this report's verified scope.

## Offline End Phase counters

Use `inspect-map` with descriptor kind `end_phase_inspection` to extend the menu report
with `counter_value` (0..3), `end_phase_count_scope` and `counted_as_unmoved` on each row.
The aggregate `unmoved_unit_count` counts scoped actors with positive counters; counter2
counts once. `displayed_unmoved_unit_count` reproduces the UI count modulo100.
`end_phase_scope_count` counts all actors in that scope, including counter0.

Exact descriptor keys: `kind`, `schema_version` (1), `menu_membership_profile` (complete
existing descriptor), `code_anchors` and `evidence_ids`. Supply defining aggregate,
resolver and UI evidence fingerprints; inherited combined32-anchor/16KiB limits apply.
There are no configurable counter offsets or count masks. The supported raw group0
count scope differs from the Ally-menu category. Enabled related-actor cases outside
the validated fallback recipe, null objects or missing/mismatched captures reject.

This reports the game's End Phase prompt counter. It does not establish whose turn it
is, whether Move or Attack is legal, or which action consumes the counter. All live and
autonomous capabilities remain false. No emulator connection or new capture is performed.
