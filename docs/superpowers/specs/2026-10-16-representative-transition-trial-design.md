# Representative transition validation design

Status: approved by the user on16October2026. This authorizes the scoped human-assisted trial only; production readers remain unchanged.

## Goal and scope

Validate that the decoded representative selection follows one reversible robot-form change
in the actual game, instead of merely matching retained snapshots. This is a research trial,
not battle acceptance or a production representative-reader feature. Existing uncommitted
implementation and staged user documentation must be preserved. No commits or publishing.

The currently approved map discovery limits inputs to cursor/info navigation. This proposal
adds exactly one eligible allied unit's visible Transform/Change command, A-to-B followed by
B-to-A when the reverse command remains visibly available. It does not authorize movement
confirmation, attack, abilities, resource spending, end-turn, dialogue choices, saving,
loading another state after startup, RAM writes, injected game calls or stage progression.
Normal form-dependent HP/EN maxima may change; do not call that resource spending, but stop
if the menu displays a cost or any unexpected HP/EN loss occurs. The preferred candidates are
Z Gundam (observed form122, alternative123) or Methuss(MA) (134, alternative133). Choose only
one, based on a fresh visible eligible command; no guessed button sequence or hidden menu.
Do not change crew assignments in this trial. That needs separate evidence/approval later.

## Alternatives and recommendation

1. Continue offline tracing only: no game mutation and already authorized, but cannot prove
   the live refresh sequence. Continue this independent work while approval is pending.
2. Recommended: one protected human-assisted reversible form trial. Causal before/after
   evidence is strong, changes are bounded to a disposable trial memory stick, and existing
   screenshot handoff avoids unvalidated automatic menu recipes.
3. Compare independent stage-state launches: useful for held-out layouts but weaker evidence
   for a specific form transition, requiring additional launch/backup and state-load scope.
   Do not perform this under the present proposal.

## Protection and ownership

Before starting, recheck process/listener state. Never close, reload, discard unsaved changes,
or bypass a warning in any pre-existing PPSSPP session. If a session exists, stop the launch
path and report that dependency; no attachment to a stale PID or concurrent controller.

While PPSSPP is closed or confirmed not writing, create fresh timestamped complete backups of
both original SAVEDATA and PPSSPP_STATE, the active portable equivalents, and configuration.
Use existing Launcher/backup services, preserve every file/subfolder and earlier snapshot,
verify every copied file with SHA-256, and save the manifest. Backup failure prohibits launch.
Keep immutable verified snapshots separate from writable trial copies; never copy trial data
back to originals. No files outside authorized project backup/trial directories may be written.

Use the existing isolated PPSSPP1.20.4 runtime and Englishv0.8 ULJS00460 v1.01 binding. Startup
from the previously authorized slot2 fixture is allowed only after this trial is approved and
fresh backup gates pass. Loading slot2 at startup is the only state-load action in scope.
Authenticate the owned loopback listener and loaded game; verify the known baseline resource
fixture before any input. Current original and portable paths/executable/ISO must be rechecked
from local configuration rather than copied blindly from stale handover text.

A single protected Python debugger owns all observations. No competing MCP/controller client.
All game navigation and transformation commands in this trial are performed by the human
user after the trial is ready. The assistant requests the exact screen/action needed and
waits for confirmation; no transformation occurs just because a timeout elapsed. Existing
safe supported capture may be requested, or a new user screenshot accepted with timestamp
and explicit label. Retained old screenshots do not authenticate a new trial screen.

## Procedure and evidence

1. Create/verify backups, start the owned isolated fixture and authenticate binding. Leave
   the loaded game untouched until identity and baseline checks succeed.
2. Announce readiness and ask the user to open the chosen eligible unit's Unit tab. Collect
   a current screen and paused memory observation A. Record form name, actor/object linkage,
   HP/EN and the representative set; capture selected-Info globals separately from menu-row
   selection. No repeated screenshots of unchanged old units are required.
3. Ask the user to return to the map and use the visible Transform/Change command once.
   Wait for explicit completion. Capture an observation B before opening Info when practical;
   inability to isolate this timing is recorded rather than invented. This optional B sample
   is diagnostic: a structurally valid source/cache disagreement may reflect deferred rebuild
   and is recorded without acceptance, recovery or another transformation. Invalid pointers,
   ownership failures or unexpected gameplay still stop immediately. Obtain a fresh Unit-tab
   screen/observation B-info to corroborate the alternate form and selected actor.
4. If the reverse command is visibly available with no displayed cost and the user confirms,
   repeat the same process to A-return. Otherwise stop after B with reversible-return coverage
   explicitly incomplete; do not reload or spend a turn to force restoration.
5. Preserve trial state and leave the user's window open. No automatic closure, discard or
   reload on errors, timeouts, missing input, cancellation or helper exit. Bounded observation
   cleanup may release controls and restore only a pause owned by that observation. Never
   toggle an unrelated user pause. Original/snapshot/config preservation hashes are checked
   after observations while those sources remain non-writing. A later manual emulator exit
   may permit final trial-copy archival, but is not required or triggered automatically.

Each observation uses the existing serialized observation_pause context, validates owned
identity and exact read lengths, and resumes only its own pause. Follow validated pointers
with RAM bounds, alignment/capacity/cycle checks; never read arbitrary windows based on a
label. Capture source actor catalogue/list, object pool, selector90-pair table, exclusion
154-ID array and127-pair table, cached linked list, dirty byte, selected-Info links, and
involved descriptor/stat records. Prefer bounded windows, max1MiB per observation. If needed
coverage exceeds that limit or a pointer/layout is unsupported, stop and document the gap
rather than silently falling back to a full-RAM/live scan. Profile/code fingerprints must
match corroborated clean instruction windows before interpreting these fields.

All raw bytes, frames and hashes remain ignored under the trial evidence directory. Record
trial/game/emulator identity, sequence, timestamps, pause before/after, exact read windows,
SHA-256, visible form labels, helper ownership and each manual action acknowledgement. A
current frame and memory sample are correlated observations, not a claim of atomic display
and CPU capture; document their ordering. No public game bytes or literal runtime profile.

## Stable observations versus diagnostic timing

A and A-return qualify as stable only after a fresh acknowledged Unit screen and two
completed, separately paused read observations, with normal running status between scopes,
agree on candidate objects, selector pairs, representative bindings and selected-Info link.
B-info uses the same rule after the alternate-form screen is acknowledged. Every stable
sample must independently satisfy all structural invariants below; a first B-info mismatch
stops the trial, without retrying or sending another input. The second observation is a
bounded corroboration read after a successful first read, not a reconnect/recovery loop.
Agreement is observed corroboration, not a guarantee of atomic frame/CPU capture.
Only optional pre-Info B is permitted to retain a structurally valid deferred-cache mismatch
as diagnostic timing evidence; it never counts toward acceptance. No unrelated gameplay,
resource loss, invalid pointer, identity or pause failure is exempted by that label.

## Acceptance and failure behaviour

Compare the complete decoded source recipe and actual cached representative SET at each
stable A/B/A-return observation. Require one representative per candidate object, no missing
or duplicate objects, all bindings drawn from the validated actor catalogue, and no unexplained
roster changes. Require the chosen object's ID/address unchanged, alternate form/pilot actor
matching the fresh Unit screen/Info links, and expected selector-pair updates. Pilot identity
must stay the same unless visible evidence explicitly shows otherwise, which stops the trial.
Do not claim cache order predicts menu order. A clear dirty bit alone cannot establish capture
coherence or completed rebuilding, because the getter clears it BEFORE rebuild. Capture the
flag as diagnostic data and validate the resulting structures directly.

Any wrong fixture, missing frame, unexpected menu, stale ownership, unknown warning, resource
cost, extra input, stable-observation roster inconsistency, unreleased pause/control, read failure or disconnect
stops further actions. Do not reconnect/replay or automatically revert. Preserve evidence
and leave the window/session for the user. Report unknowns and whether the reverse change was
actually corroborated. This trial can validate one form-change lifecycle only; crew changes,
stage transitions, save/load recovery and universal gameplay semantics remain unverified.

## Follow-on work

Only after written approval: write the exact bounded execution plan with writing-plans,
review the private helper's no-close/error behavior with synthetic tests before any emulator
launch, and execute the procedure. Production modules and command output remain unchanged.
A later representative-inspection API or live tactical integration needs its own evidence-bound
written design and review. Never enable run or tactical/autonomous capability flags here.
