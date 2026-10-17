# Session handover — 17 October 2026

Read this first, then AGENTS.md and approved specs/plans. User paused for a break,
will commit independently and resume in a new chat tomorrow. Assistant must not
commit, launch more trials, send game input, close/reload the emulator or continue
research during this break. Existing edits are authorized ongoing work; preserve.

## Completed today

Dedicated DebuggerAdapter.read_original_code uses PPSSPP replacements=false under
owned paused/bound scope for exact instruction fingerprints; ordinary game data
retains replacements=true. Root cause was native JIT RUNBLOCK words replacing two
instructions at0x088A2AAC. No masking/removal of checks. Full configured source suite
1092 passed,1 Windows symlink privilege skip; strict mypy31 modules, Ruff, wheel/help
passed. Independent adapter/integration reviews cleared.

Protected human Z Gundam Move/Attack succeeded with two stable captures at every
stage. Move(18,13)->(14,15), EN128->122, HP4700 unchanged. Forecast BeamRifle97%
against Euclid HP5211 EN89, counter49%, support Taurus HP2603. Postcombat ZHP1119,
TaurusHP450, EuclidHP5211 EN74. All26 remain, exact code checks pass through combat.
User confirms Z greyed out/no command menu. Candidate old EndPhase counter remains1;
NOT authoritative can_act. Production autonomous run remains disabled.

Offline candidate bytes: object+0x25 Z0A->08->60; object+0x60 40->40->00.
Unused Destiny HP5200 EN230 uniquely maps object149303288/mech197/pilot208,
rawgroup0,tile(19,5); user sees Move/Attack/Spirit/Info; retained status0A/40.
No defining command availability predicate yet; do not promote candidates.
User movement cheat writes0C to object+8 over99slots/stride104. Counter only uses
bits3..4; whole-byte reset changes more. Bit5 traced to mode-specific tile actor
selection0x088AB6D8/0x088E5E2C, with alternate unfiltered selector0x0883BD48;
not universalcan_act. Other infinite-action patch address0x089594F4 maps to apparent
text/display handling in retained build, unverified, never applied.

## Next authorized task

Human Destiny move one tile down then Standby, diagnostic only (MVP stillMove/Attack).
New private standby_handoff.py implements baseline->unit-baseline->move-preview->
post-move->post-standby. User proposed/approved this session; no repeated approval
questions for agreed testing. Must collect actual unconfirmed preview, confirm move,
capture, then Standby/capture. Exact downone, strict Destiny Info binding, unchanged
nonchosen resources/tiles/identities, livingallies, two stable observations, raw
+8/+0x25/+0x60 explicitly stable from hashverified data spans. Failure latches reads
disabled. All149 helper tests/Ruffpass, independentreviewcleared. No production
source changed for diagnostic extension.

The original helper could NOT capture user's first Destiny preview (state machine
finished); no capture was claimed. User subsequently closed PPSSPP normally and
approved fresh Destiny-only launch. No repeat Zattack required.

## In-progress trial at break (verify actual state tomorrow)

Fresh original SYSTEM snapshot verified at
backups/destiny-original-config-20261017T110005Z-6d2e11c6140940088db2da8515649133.
Started standby helperPID17032, childPID1540; lastread showed noPPSSPP process,
empty evidence and no stderr, consistent with complete save backup/hash preparation
still underway. It may finish and launch after this handover; DO NOT assume closed
or ready. Helper only performs initial baseline and then waits; sends no gameinputs.
Active pointer local/move-attack-trial-20261017/active-destiny-run.json;
evidence local/move-attack-trial-20261017/destiny-run-20261017T2100096872/evidence.
Read ready/prepared/fatal/disabled/stdout/stderr and verify actual PID/listener before
any action. Preserve any open window and unsaved state. Do not reconnect/replay an
error or reuse launch receipt. Complete originals+portable saves/config SHA256 gate
is enforced before launch. Never copy trial saves back to originals.

Older successful Ztrial pointer active-run.json, evidence
run-20261017T1940593206/evidence. That emulator was closed normally; all old captures
retained. All private helpers/captures live under ignored local/ and WILL NOT enter
a normal Git commit. They remain available in this same local checkout. A fresh
clone will need their recreation/secure transfer; never unignore raw game dumps,
private profiles or saves just to commit. Specs/plans/research documents are normal
untracked workflow artifacts and should be included in the user's intended commit.

## Resume prompt

Read docs/research/2026-10-17-session-handover.md and AGENTS.md, verify current Git
and PPSSPP/helper state, then continue the approved Destiny Move/Standby diagnostic
from its next uncaptured checkpoint. Preserve all save protections, no commits or
cheats, no uncontrolled restart, no additional MVP commands. Check5hour allowance
at boundaries and stop substantialwork below10% remaining.
