# PSP Buddy

PSP Buddy is a planned autonomous play assistant for **Super Robot Wars Z2 Rebirth (English v0.8)** running in **PPSSPP** on Windows. It aims to follow the user's natural-language tactical instructions and hand control back when help is needed.

## Planned capabilities

- Load and save progress using PPSSPP's existing save-state features, with support for starting from normal in-game saves.
- Read the current game state, including robot specifications, pilot statistics, map information, and battle status.
- Make tactical decisions, perform battle actions, and skip positively recognized decision-free dialogue.
- Retry confirmed allied defeats from one verified checkpoint, with at most three reloads, then hand over on map completion or a safety stop.

## Current status

The Python package includes protected launch/debugger/capture services, bounded robot and pilot inspection readers, conservative screen classification, local tactical and reaction rules, offline single-slot checkpoint contracts, a generic bounded action executor, and a safety supervisor. A synthetic two-turn scenario composes the actual executor and checkpoint services to exercise save-before-end-turn, reaction-only retries, budget reset, and map-clear handover.

The CLI supports read-only `validate` capability reports, offline `inspect --record` decoding and `inspect-map --records` reports for named records or bounded structural unit-pool spans, with explicit unknown map fields. These commands use supplied local files; they do not launch PPSSPP, connect to its debugger, save, or send game input. `run` remains disabled. See [development usage](docs/usage.md) for commands, profile format, and supported instructions.

Portable PPSSPP v1.20.4 has loaded tested saves, produced inspected screenshots through supported Windows menu control and the screenshot collector, and moved the cursor by one tile. Named pilot SP, maximum SP, level and will match fresh visible screens. Static information-screen anchors passed a separate protected launch of the same fixture, while map and command menus remained unknown. Named-unit/pilot inspection does not establish a complete tactical snapshot. Full roster/tactical decoding, unattended capture triggering, live save/load, production menu recipes, and autonomous battle acceptance remain unverified.

Verification on 13 October 2026: 545 offline tests pass; Ruff `check .` and strict mypy `src` pass. Passing these checks does not enable autonomous play.

On 14 October, the locally installed MCP 0.2.0 passed protected live mech/pilot memory reads
that exactly matched Python records and the known fixture statistics. Save/configuration
preservation passed. A separate capture trial stopped before a frame could be accepted;
deployed roster, coordinates and map decoding remain unverified. See the
[map-inspection plan](docs/superpowers/plans/2026-10-14-map-inspection.md).

14 October inspection checkpoint:603 offline tests, Ruff, strict mypy and wheel build pass.
The retained MCP-record inspect-map demo passes with deployment/map fields explicitly unknown.
Final independent whole-change review remains pending; full live map inspection is incomplete.

16 October structural inspection: the bounded unit-pool reader preserves all form/crew aliases and reproduces three retained map states. All 707 offline tests, Ruff, strict mypy and wheel build pass; independent review found no issues. Supplied spans remain unauthenticated and tactical fields remain unavailable. See the [reader usage](docs/usage.md#offline-structural-unit-pool-inspection).

The initial milestone is one autonomous battle from an existing save, with one working checkpoint slot, up to three retries, and automatic handover. See the [MVP design specification](docs/superpowers/specs/2026-10-10-autonomous-battle-mvp-design.md) and [integration research](docs/research/2026-10-10-hybrid-feasibility.md).

## Save protection

Before every emulator or game trial, back up both complete PPSSPP directories: `PSP/SAVEDATA` and `PSP/PPSSPP_STATE`. Verify all copied files using SHA-256 before proceeding. Preserve earlier backups and do not test while saves are being written.

Backups, game images, and emulator save data are excluded from Git. Supply your own game and saves; they are not distributed with this project.

## Development workflow

Use the global development workflow and this repository's `AGENTS.md`: check Git status, approve the design, write a spec and implementation plan, implement with tests, verify behavior, and review changes. Leave all changes uncommitted until the user explicitly requests a commit.

16 October geometry evidence: supplied private named-record profiles now report direct tile
coordinates and dimensions for 69/12/26 candidate records across three retained maps, with
live/tactical capabilities still false. See the [progress summary](docs/research/2026-10-16-map-evidence-summary.md)
for working software, verified evidence and remaining gates. The approved protected form
trial completed successfully and corroborated current-record selection through a reversible
change. Transform actions remain outside the MVP.

Offline `inspect-map` also accepts an explicit `representative_inspection` descriptor to
select one source/cache-consistent form/pilot record per candidate object and report its
corroborated HP/EN/SP/DEF/MOB/HIT. It rejects unsupported or inconsistent supplied spans;
all live/tactical capabilities remain disabled. See [usage](docs/usage.md). Transformation
actions are outside the MVP; the form trial supplies reader evidence only.

For robot positions, the explicit `positioned_representative_inspection` descriptor adds
zero-based tile coordinates and bounded map dimensions to the offline selected-robot
report. Supplied capture provenance and disabled battle capabilities remain unchanged.

The explicit `menu_membership_inspection` profile further reports Ally/Foe menu membership
with the same selected stats and tiles. Units outside both menus remain outside; hostility
and tactical allegiance are still unknown. It is offline and does not enable battle actions.

The offline `end_phase_inspection` descriptor adds per-unit two-bit counters and the
verified End Phase “Unmoved Units” count to the existing stats/tiles/menu report.
It preserves unknown Move/Attack legality and all disabled live capabilities; see
[usage](docs/usage.md#offline-end-phase-counters).

MVP player-unit commands are **Move and Attack only**. Repair means healing and is
excluded, together with Spirit/Trust, Supply, Transform and crew changes. Unknown healing
capabilities do not block Move/Attack planning; existing retreat safety remains.
