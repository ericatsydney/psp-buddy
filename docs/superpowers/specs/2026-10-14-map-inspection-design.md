# Read-only battle-map inspection design

## Approved goal and implementation boundary

The user approved the read-only battle-map milestone and requested implementation on
14 October 2026. Stop work when the account's five-hour remaining allowance is below 10%;
check usage at task/trial boundaries. Preserve work and close owned processes before handover.
No automatic commits, pushes, save/load commands, battle actions or original-save writes.

## Approach

Keep the protected Python runtime and use MCP for bounded inspection research. A direct
MCP-only runner would duplicate safety contracts; a screenshot-only map reader would depend
on unresolved recognition and text decoding. The recommended hybrid reuses validated memory
primitives and visible corroboration, then decodes evidence-bound records locally.

## Discovery phase

Use existing launcher/backup services to create fresh complete SHA-256-verified backups of
original and active portable SAVEDATA/PPSSPP_STATE and configuration before each trial.
Back up while PPSSPP is closed; backup/hash failure prohibits launch. Operate the isolated
owned runtime only. Verify original/snapshot/archive hashes after closure. Never copy back.

Confirm PPSSPP 1.20.4, ULJS00460 version 1.01 and the supplied English v0.8 image binding.
Authenticate the owned loopback listener before MCP startup. Use one controller at a time.
Read known named unit/pilot records through the actual installed MCP, compare exact bytes
against existing decoders, and record private identity/provenance/hash evidence.
Use Python observation scopes for coherent multi-block samples and explicit pause cleanup.
MCP reconnect or uncertain identity invalidates further reads until revalidation.

Correlate bounded regional samples with fresh visible maps/info screens. Allowed trial
inputs are single short directional cursor presses, cancel and positively recognized
information-panel/menu navigation; no movement confirmation, attacks, end-turn or saves.
After each input verify the screen and release acknowledgement before another input.
Unexpected menus or inability to obtain a current frame stops input discovery.
Keep raw bytes/images/private labels under ignored local/backups paths.

Validate active roster count/IDs, affiliations, coordinates and action status against several
visible units and inactive/reserve negatives. Validate candidates after a separate fresh
backup/reload; map dimensions, occupancy and terrain need independent visible evidence.
Do not promote cursor coordinates to unit positions or adjacent stat records to deployed units.
Report partial progress honestly if cross-map or roster evidence cannot be established.

## Reader/report phase

Add a separate offline map-inspection interface rather than changing tactical Snapshot.
Its immutable profile binds game/patch/emulator identity, bounded memory spans, explicit
unit identity/field bindings and evidence references. Memory input must be immutable bytes
of exactly the required length. Decode unsigned little-endian fields only when the evidence
defines their layout and meaning. Bound coordinates by corroborated map dimensions;
reject duplicate unit identities, overlapping/malformed layouts and inconsistent HP/resources.
Unvalidated positions, side, action availability and SP are null with an explicit reason.
Never infer deployed membership from a user label or claimed evidence references alone.

An offline `inspect-map` command consumes supplied configuration, profile and captured
records without launching or connecting. Output contains identity, known unit records,
explicit roster-completeness status, corroborated values, missing fields and supplied-input
provenance. It must not claim live authentication or enable planning/autonomous execution.
Until complete roster evidence exists, label records as named inspections rather than a
complete deployed roster. Pure tests use synthetic bytes, never real game data.

## Acceptance and failure behavior

1. Actual MCP known-record read works under a protected owned trial, with exact byte counts.
2. Candidate map fields have visible corroboration and held-out reload evidence; otherwise
   retain them as research-only and report inspection incomplete.
3. Reader/report rejects malformed layouts, mismatched identity, truncated records, invalid
   coordinates/resources and unsupported evidence claims. Unknown remains unknown.
4. Tests demonstrate no live fallback, no tactical Snapshot construction and no input/save.
5. Full offline pytest, Ruff, strict mypy, wheel build, CLI checks and code review pass.
6. The final report states exactly which map capabilities are verified and which remain blocked.

Implementation is staged so independently verified inspection tooling can be delivered even
when discovery fails; that partial delivery does not satisfy full map-snapshot acceptance.
