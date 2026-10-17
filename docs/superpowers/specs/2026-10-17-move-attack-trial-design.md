# Protected Move then Attack observation trial

Status: concrete written trial approved by the user for this testing session. Do not ask
for repeated approval within this scope. Human action acknowledgements remain required. No commits.

## Purpose and alternatives

Establish how one actual Move and, if legal afterward, one Attack affect direct unit tiles,
the two-bit counter and the End Phase count. Keep command visibility separate from memory
correlation; a positive counter alone does not prove command legality.

Recommended: bounded human-assisted trial with assistant-owned read-only observations.
Offline code tracing cannot establish causal consumption. Autonomous menu execution is
premature while recipes/phase/legal-action observations remain unvalidated.

## Exact scope

One selected living player-controlled ally, one confirmed Move to an empty visibly legal
tile, and at most one visible post-move Attack against a clearly hostile living target.
Human performs every game navigation, move/weapon/target selection and combat confirmation.
No guessed button sequences, RAM writes, injected calls or automatic combat inputs.
Prefer a nearby ordinary foe and a non-MAP weapon with sufficient visible EN/ammo; exclude
weapons that may damage allies. If hostility or eligibility is uncertain, stop before input.
Do not use Wing Zero solely because it is outside Ally/Foe lists; its hostility is unknown.

Exclude Repair/healing, Spirit/Trust, Supply, Transform and crew changes. No assistant
Wait/End Turn, enemy-phase progression, saving, rollback or reload after startup. Movement
may be provisional until the next command: record this accurately instead of claiming a
committed tile or navigating away to force commitment. If Attack is absent after movement,
record that negative and stop; do not issue Wait to manufacture another counter sample.
Standalone Attack without prior movement is outside this first sequence's acceptance.

## Save protection, startup and ownership

Recheck processes/listeners/config paths immediately before preparation. Preserve any
existing emulator session, warning and unsaved changes; no close/discard/reload or takeover.
Existing process/listener blocks launch until resolved by the user. No stale PID reuse.
While closed or confirmed not writing, create fresh complete timestamped original AND
portable SAVEDATA/PPSSPP_STATE/config backups, verify every copied file SHA-256 and manifest.
Failure blocks launch. Reuse existing protected Launcher services. Immutable snapshots and
writable trial trees remain separate; no trial data copied back. Preserve earlier backups.

After written approval and tested helper review, startup from the existing slot2 fixture
is the sole state-load action in scope. Verify current executable/ISO/config and bound
PPSSPP1.20.4/ULJS00460 v1.01 Englishv0.8 identity; authenticate one owned debugger listener.
No competing MCP/controller clients. Stop on baseline mismatch. Leave the emulator open
on failure/cancellation; do not use an error path that terminates it. Every task/trial
boundary checks quota and stops substantial work below10% five-hour allowance remaining.

## Procedure and evidence

A. Human opens the chosen ally's Unit tab and supplies one current screenshot if needed.
Capture two separately paused stable baseline observations, with normal running between.
Require source/cache agreement and validated roster, tiles, stats, group/counter fields.
Bind chosen unit by object+mech/pilot identity and visible HP/EN; selected-Info links may
corroborate this baseline only. Record the initial End Phase count without opening its
confirmation. No repeated old unchanged robot screenshots are requested.

B. Human opens Move and selects one visibly legal destination. Before confirming, record
the current movement overlay/target tile when supported, or obtain a user screenshot.
Human confirms Move and replies ready. Capture current map/command-menu frame and two
stable memory observations. Do NOT require opening Unit Info here: that may cancel a
provisional move, and stale Info links are not authority for the moved unit. Follow the
baseline object/identity through validated representative data and record whether the
menu explicitly offers Attack. Distinguish preview/provisional position from committed
position and record unavailable moved-state semantics honestly.

C. Only if a current screen shows legal Attack, human selects a valid hostile target and
weapon. Capture pre-confirmation preview with visible weapon cost, target HP and any
counterattack forecast. User explicitly confirms combat after seeing that preview. If
selection is unsafe/ambiguous or a warning appears, stop and request user handling.
One attack may spend EN/ammo, damage both units through a counterattack or defeat the
chosen foe. These are expected possible effects of this one human-confirmed combat; no
claim of unchanged combat resources. Avoid a last foe/stage completion trigger when
visibly identifiable. Unexpected dialogue/choices, allied defeat, map clear or phase
change stops all assistant input; never acknowledge prompts or retry combat automatically.

D. After human reports combat resolution, capture the settled map and two stable memory
observations when normal running permits. Compare chosen tile, counter, scope/count,
HP/EN and target changes. Record ammo/damage as unavailable unless independently visible
and decoded; do not invent offsets. If source/cache changes for a defeated foe, validate
current roster rather than demanding unchanged candidate count. Unrelated roster or
identity changes are diagnostic and block acceptance until explained. Never reload to
undo this sequence. Preserve trial state and leave the user's window open.

## Helper and failure rules

Use a new ignored helper under local/move-attack-trial-20261017, reusing reviewed backup,
no-close ownership and serialized observation_pause primitives. Do not alter/reuse old
form-trial state labels as though they validated combat. Requests require trial_id,
monotonic sequence, exact stage and explicit human acknowledgement. No time-based actions,
reconnect/replay or automatic launch retry. Human absence leaves an idle open session.

Bound each observation to1MiB total and64KiB per read, validate all pointers/list capacities,
identity/code fingerprints and exact lengths. Capture the supported object/source/cache/
selector/exclusion/stat/dimensions/group/counter windows and relevant UI evidence only.
No fallback to full-RAM scanning. Restore only an observation-owned pause; user pause or
uncertainty stops observation. Record frame/read ordering as correlated, not atomic.

Tests with fake process/session/adapter must prove: no press/save/load/close/terminate on
request/error/cancel, stage sequencing/ack validation, bounded reads, selected-Info staleness
not falsely promoted, stable source/cache validation, and resource changes across combat
accepted only as observed evidence. Failure disables further collection, releases owned
controls and preserves session; no retry or forced commitment.

## Acceptance and next boundary

A valid record provides baseline, post-Move menu and post-combat observations for the same
unit, with actual counters/tiles and explicit visible command evidence. Record partial
coverage if Attack unavailable, movement provisional, user absent or combat unresolved.
No universal action_available/moved enum is promoted from one sample; extra-action units,
standalone attack, terrain/range and cross-stage legality remain separate evidence needs.
No production planner activation or autonomous battle acceptance follows from this trial.

Self-review: one unit/one Move/at mostoneAttack, human-only confirmations, resource loss
and provisional movement treated explicitly, original and portable saves protected,
no implicit reversal or End Turn. Written review is approved; helper verification and fresh backups precede startup.

## Diagnostic replay clarification

Userexplicitlyrequestedrestartandreproductionafterthefirstfailedforecastcapture.
Preserve an identity-anchor mismatch as a private forensic artifact: exact address,
size<=4096, expected/observedSHA256 and exactalready-readbytes. No extra memory read,
new address, fingerprint relaxation or accepted observation follows. Validate artifact
bounds/length/hash beforewriting; failurestilldisablescollectionevenifforensiclogging
fails. This extends existingprivatebyteevidencelogging for failedratherthansuccessful
observations. Restartusesfreshcompleteverifiedbackupsandhumanselectedcommands.

## User-requested ready acknowledgements

Userprefersreadyaftercontrolsand screenshots onlywhennecessary. This supersedes the
every-stageframe requirement for manual research checkpoints, not autonomous legality.
Recommended: explicit human_ack evidence mode for Unit baseline,Move preview,postMove,
postcombat andpartialstop; battle attack-preview still requiresfreshimage. Keeping all
imagesforcesredundantcaptures; silentlyreusingoldimagesorfabricatingnewonesisforbidden.
Human_ackrequest uses evidence_mode=human_ack,acknowledged_at (awareUTC<=5minold,
>=helperstarted,strictlymonotonicacrossallstages),acknowledgement_text(nonemptybounded),
no screen_path/timestamp. Exactstagefields/sequence/trial/safe-playeracks unchanged.
Unitbaselinehuman_ack additionally requires freshdiagnosticselectedInfo.corroborated
andcurrent_binding matching boundrepresentative inBOTHobservations. Neverlabeltext
evidenceasaframe; reports screen=null andmanual_evidence.type=human_ack, preserving
itsactualmodality. Moveoverlay/Attackavailable remain humanattested whennoimage;
notpromotedtomemory-verifiedlegalactions. All existingidentity,stabletwo-read,
roster,tile,target/resource,forensic anddisableguardsremain. Image-mode compatibility
remains, no code/adapterreadchanges. No fabricatedimagereferences. Runtimeupdate
needsreviewedfreshrestart; preserve currentwindowuntil thatstepisauthorized/handled.

TextUnitbaseline uses expected_mech_id,expected_pilot_id,expected_hp,expected_en
inplaceofvisible_* fields. Theseareexpectedbaseline/currentmemoryvaluestovalidate,
notclaimedhumanvisualtranscriptions. BothfreshInfoobservationsmustmatchtherow.
Postmove/othertextstagesclaimboundrepresentativememoryandhumanUIattestationonly;
partialstoprecordsexplicitlynomemoryobservations.

## Observed enemy support defender in the one-attack trial

Both supplied forecasts explicitly show TaurusHP2603 as enemy support defender. This
is an enemy combat response, not use of the excluded player Support command. A fresh
attack-preview image may name one optional support_defender_object plus its visible
support_defender_hp. Both fields must appear together, identify a distinct living
Foe-menu row (rawgroup12..15), match its current HP, and differ from chosen ally/main
foe. Preserve these roles/precombatvalues explicitly. After the single confirmed combat,
permit disappearance of only the declared main foe and/or declared support defender.
Every other actor binding remains fixed and living allies remain present/alive. This
explains the known enemy response without accepting arbitrary roster changes. Old
requests without support fields retain main-target-only behavior. No extra input,
read, player Support/Spirit command, reload or retry is added. Test meaningful rejection
of undeclared casualties, invalid/duplicate/ally/dead defenders and mismatched HP.
