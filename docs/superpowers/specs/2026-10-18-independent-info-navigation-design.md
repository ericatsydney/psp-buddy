# Independent navigation to Destiny Info

Status: proposed; explicit user request is to move the cursor to Destiny, open its
command menu, choose Info and capture the screen without human navigation/readiness.

## Scope

Automate observation-only game navigation for the existing fixture. No unit Move,
Attack, Standby, End Turn, save/load, cheats, memory writes or automatic emulator closure.
Do not broaden this request into battle automation. Preserve the existing protected
session/backup and uncertain-outcome rules.

## Approaches

1. Recommended: extend the project-owned MCP bridge and a new private helper entrypoint
   with bounded timed navigation requests, using the same owned debugger adapter and
   investigation lock as memory collection. This avoids missed short OS key taps and
   a competing debugger controller.
2. Generic upstream MCP input server: fewer changes, but creates a second independent
   controller and bypasses existing launch binding/serialization. Do not use it directly.
3. Computer Use game keys: no new implementation, but current protected trial's Right,
   Down and Circle-mapped x taps produced no visibly accepted transition. Root-window
   focus click failed with unavailable coordinate geometry. Windows screenshot/menu
   keyboard control still works. Do not blindly repeat uncertain navigation.

## Interfaces and flow

New MCP request describes the intended navigation step, trial ID and source evidence,
not an arbitrary raw debugger command. Allow directional cursor taps, cancel and a
confirm only against an independently observed map/unit-command/Info-menu context.
Use finite PPSSPP input.buttons.press durations (initial2frames, maximum3), explicit
release/timeout handling and a small total input budget (at most16taps for this route).

Read the supported fixture's current state through the existing coherent observer.
Bind Destiny to mech197/pilot208/object149303288 and its current bounded tile; known
baseline is HP5200/EN230 at(19,5). Do not mistake cursor fields for unit coordinates.
Use screenshots when required to verify current cursor/menu state; group harmless
directional steps only after input response and cursor convention are established.

Open the unit command menu only after selecting the target. Inspect available commands,
navigate to the visibly identified Info entry, then confirm and capture. Verify the final
name/stats and selected Info memory binding agree. Stop if any step is unsupported,
ambiguous, stale or reaches an unexpected menu. Never confirm Move/Attack/Standby.

Keep the successful screenshot route: agent-controlled Windows Debug > Take screenshot,
regular fresh JPEG validation and local evidence retention. MCP GPU capture remains
unavailable; do not retry it. Screenshot acquisition and memory samples must report
their actual timing, not claim atomicity.

No synthetic human acknowledgements. The new navigation evidence must distinguish
agent-issued input and agent-observed screen from prior human-controlled trial stages.
If the existing Standby stage schema requires human acknowledgement, keep it unchanged
and record this new Info-navigation result separately until its contract is extended.

## Implementation/activation boundaries

TDD: request schema/tool allowlist, stale trial/evidence refusal, whole-operation lock
and deadline, finite taps/release, wrong cursor/menu/identity stops, no dangerous command
confirmation, final image/memory binding. Run source/private/Node regressions and static
checks/build; independent review must clear before activation.

Use a new helper entrypoint and fresh verified original/portable saves/states/config
backups. Do not hot-patch or attach a second controller to the current waiting helper.
Normal closure is needed once for activation; routine subsequent navigation/Info
screens will be performed by the agent without requesting human ready at each step.

Acceptance: agent reaches Destiny's Info from the map, obtains and validates the screenshot
and memory identity, with no human cursor/menu input and no battle/save changes. Record
inputs, small milestone screenshots, final stats and preservation evidence locally.
