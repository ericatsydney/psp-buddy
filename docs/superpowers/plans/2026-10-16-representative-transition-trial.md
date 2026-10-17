# Protected representative-transition trial execution plan

> **For agentic workers:** Use bounded disjoint private-helper tasks, TDD and independent review. User instructions prohibit commits. This is the approved research trial, not a production feature.

**Goal:** Launch one freshly backed-up slot-2 session and collect bounded read-only observations around one human-performed reversible form change.

**Architecture:** A private bounded collector captures source/cache/selector/object evidence through the existing owned debugger observation scope. A private request-file server controls only collection; all game inputs belong to the human. It never closes, reloads or saves the emulator. Existing Launcher handles verified snapshots and isolated startup.

**Tech Stack:** Python, existing PSP Buddy Launcher/DebuggerAdapter, pytest, asyncio and JSON. Source modules are unchanged.

Approved design: docs/superpowers/specs/2026-10-16-representative-transition-trial-design.md. Prior707tests/static/build checks passed; current tree is authorized uncommitted work.

## Task1: Bounded collector (collector worker)

Files: local/transition-trial-20261016/collector.py and test_collector.py only.

- [ ] Write a failing private test importing the collector, then observe missing-module red with `.venv/Scripts/python -m pytest local/transition-trial-20261016/test_collector.py -q --basetemp=local/transition-collector-red-20261016 -p no:cacheprovider`.
- [ ] Expose async collect_observation(adapter) -> dict, with one observation_pause scope per call, max1MiB total bytes fetched, validated RAM addresses/windows, <=64KiB per read, immutable returned span evidence. Every exact read length and pointer alignment/capacity/cycle bound is enforced. No fallback full RAM or injected game code.
- [ ] Follow actual source root chain, source/cached linked lists, validated actor catalogue, pool224*104, selector90*8, exclusion154*4 and127*20, selected-Info links and selected descriptor/stat windows. Decode representative source recipe exactly as existing private research; compare sets/candidate joins. Gather code anchors only where bytes match both clean states AND retained live sample; reject mismatch, never ignore emuhacks.
- [ ] Cache/merge known required reads to avoid per-node round trips; finite corroborated node spans and descriptor batches are allowed within budget. Save exact captured windows/hashes and source/cache/pair/selected/geometry/resource summaries. Missing required coverage fails explicitly.
- [ ] Test against a fake adapter backed by retained RAM (private-only), reproducing69/12/26 and stable linkage; test malformed/null/misaligned/cyclic pointers, wrong identity/anchor, short reads, byte budget and pause cleanup on failures. Unsupported layouts stop, never heuristic select firstpilot.
- [ ] Run focused tests, Ruff and available type checks. Root reviews coverage and field mappings before dependency integration. Collector performs no filesystem persistence or emulator launch/press/save/close.

## Task2: No-close human handoff server (helper worker)

Files: local/transition-trial-20261016/handoff.py and test_handoff.py only. Import collector after interface ready; do not edit it.

- [ ] Write failing safety tests before helper implementation. Use fake process/session/adapter: collection error, cancellation, unknown request and disconnect must never call session.close, process terminate/kill, adapter.press or save/load.
- [ ] Expose async serve(session, adapter, evidence_dir, collector=...) using atomic exact request JSON, monotonically increasing sequence, matching trial_id and explicit user_acknowledged. Accept baseline/A/B-diagnostic/B-info/A-return labels only. Stable requests collect twice in separate scopes; require normal running status between and matching candidate/source/cache/selector/selected relationships. Diagnostic B may record structurally valid source/cache mismatch only. Invalid pointer/identity/pause failures disable reads.
- [ ] Server remains idle until explicit request; no game navigation or time-based continuation. Record errors and preserve window. A failed read disables further requests, no reconnect or replay. On helper cancellation/exit, bounded adapter cleanup only; never emulator closure. Tests must prove this state behavior.
- [ ] Main entry checks no pre-existing PPSSPP/listener before preparation, uses existing validated local config and Launcher.prepare with existing slot2 filename and fresh original+portable save/config backups. Verify receipt before Launcher.start. Authenticate adapter and baseline known G00 HP5000/EN121/SP55. Record ready.json with PID/trial/manifest/paths and baseline result. No navigation or transformations.
- [ ] Keep errors observable in files/logs, leave emulator open even if baseline fails after launch. If preparation fails before launch, do not start. Use hidden background process for persistent server, with logs in ignored trial directory. Do not reuse stale helper PID/connection.
- [ ] Run focused safety tests and Ruff/type checks. Root reviews before any invocation of main.

## Task3: Preflight, review and protected startup (root)

- [ ] Review new private files and intended workflow docs. Run both private suites, applicable existing launch/debugger/backup tests and Ruff. Full suite may run once if quota permits; source is unchanged. Any blocking failure prevents launch.
- [ ] Independent code/safety review checks all no-close, no-reload, pause, byte bounds, identity, stable-vs-diagnostic and trial scope gates. Fix Important findings and rerun affected tests.
- [ ] Recheck quota (do not launch below10% remaining), current process/listener state, real source/config/executable/ISO paths. Verify save sources not writing. Start the reviewed helper, which creates fresh verified complete snapshots BEFORE launch. Inspect manifest and ready/error records; do not merely assume prepare succeeded.
- [ ] Preserve original/immutable hashes and old backups. A process already open stops startup without closing it. Any prompt remains for the user; no discard.
- [ ] Once baseline ready, tell user the emulator is loaded. Ask for Z Gundam's Unit tab first (or Methuss if visibly eligible; one unit only). Request a new transition baseline screen, not repeated unchanged-unit research. Wait for user response before collection A or form changes.
- [ ] Subsequent B/B-info/A-return steps follow approved spec, explicit human acknowledgements and new screens. Never turn elapsed waiting into approval. Every trial/task boundary checks quota. If user absent, leave session open and continue only independent offline work.
- [ ] Record exact completed gates, PID/helper evidence and next request index. No final closure or reload. Trial remains incomplete until actual A/B/A-return corroboration.

No commits, pushes, production changes, battle actions, saving or automatic emulator closure. No further permission request is needed for this approved trial scope.

## Integration review continuation — 16 October 2026

The current implementation deliberately rejects optional B-diagnostic requests before any
read. Pre-Info selected globals may be stale, so resource continuity cannot be authenticated
there by this helper. This records the optional timing coverage as unavailable; use A,
B-info and A-return with fresh Unit screens. The approved trial scope is unchanged.

Initial focused run: 142 tests passed. Full offline suite: 707 passed; Ruff on src/tests and
strict mypy on all 23 source files passed. Initial sandbox runs failed on temporary-directory
permissions; the same focused suite passed with normal filesystem access. No emulator trial
was involved. Collector/handoff retained-RAM composition baseline also passed.

Review corrections in progress: enforce both one-to-one candidate-coverage flags for stable
observations (two meaningful failing regressions observed before fix); reject optional
diagnostic phase; preserve all unrelated representative bindings across phases; require
selected Info to match its representative; validate resource bounds; remove duplicate
consumption of the one-use backup receipt before Launcher.start. Final checks and independent
re-review must pass before launch. Configuration is copied privately from the existing valid
CLI configuration; every source, executable, ISO and profile exists, slot2 is present, and
no PPSSPP process or debugger listener was observed at preflight. Recheck before startup.

## Usage-boundary handover — 2026-10-16

User explicitly approved the representative-transition design. Approval persists; do not ask again for the agreed trial. Five-hour usage check reached 94% used (6% remaining), so work stopped before integrated verification/review and BEFORE emulator startup.

Private collector: local/transition-trial-20261016/collector.py and test_collector.py; author reports 27 tests passing, Ruff and mypy clean, 13 retained RAM sources covered. Private handoff: handoff.py and test_handoff.py; author reports 22 fake safety tests passing and Ruff clean. Root has read implementation but final independent/integrated review is NOT complete. No main invocation or emulator launch occurred.

Next: check quota and repository/process state; run combined private tests and applicable launch/debugger/backup tests, Ruff, then independent safety review. Verify collector/helper schema integration, source/cache equality, form/phase/resource/fresh-screen gates, and no-close wrapper on every startup/error path. Preserve all existing staged and unstaged authorized work. Generate absolute-path JSON config from local/validated_capture_trial.py config (safe import), then use helper's Launcher.prepare/start for fresh complete SHA256 original+portable saves/states/config backups. Do not bypass backup/ownership gates. Start background helper hidden only after verification passes, unique empty evidence directory, PYTHONPATH=absolute src, no automatic retry if startup fails. Keep PPSSPP open on all errors. After ready.json confirms slot2 baseline G00 HP5000 EN121 SP55 in two observations, ask user to open Z Gundam Unit tab and provide fresh screen, without transforming yet. No automatic game inputs or saves. Record actual PID/manifest/evidence path for next handover.

Helper request protocol: trial_id, next sequence (baseline internal1; A starts2), label A/[B-diagnostic]/B-info/A-return, user_acknowledged true, fresh screen_path, visible_form integer, timezone-aware screen_timestamp within5min and after helper start. A eligible mech122 or134; paired B123 or133; same object/pilot/roster, SP unchanged, no unexpected HP/EN loss. Every stable phase takes two separate bounded paused observations; errors disable reads permanently without reconnect/replay/closing emulator.

## Final prelaunch verification — 16 October 2026

Integrated private/existing safety suite: 161 passed (68 private composition/collector/handoff
checks plus 93 existing launch/debugger/backup checks). Full offline suite707passed; Ruff
src/tests/private helper and strict mypy src23files/collector passed. Independent rereview:
no Critical or Important findings. Minor: manually inspect selector-pair deltas before
claiming lifecycle acceptance. No production code changed during this continuation.

All listed integration corrections above are implemented and tested, including stable tile
geometry (dimensions plus object/tile coordinates; excludes raw pixel animation) within and
across phases. Backup receipts are consumed once by Launcher.start, never preconsumed.
Fresh startup requires all gates again; approval remains valid.

First helper invocation stopped before backup/start because stdout/stderr files occupied
its required-empty evidence directory. No emulator was created. Corrected orchestration
places logs in the parent, with a new evidence subdirectory. Background helper PID7660,
evidence local/transition-trial-20261016/run-20261016T175435/evidence; active-run.json is the
machine-readable pointer. Startup/backups currently pending; do not claim readiness until
ready.json and manifests are checked. No retry after any emulator spawn failure.

## Live startup ready — 16 October 2026, 17:57 AEST

The approved protected slot2 startup succeeded. Helper PID7660 (venv wrapper; child6832),
owned PPSSPP PID14684. Trial20261016T075445338602Z-e3804b5a17964b04b11a3126525f2f93.
Machine-readable pointer local/transition-trial-20261016/active-run.json; evidence
local/transition-trial-20261016/run-20261016T175435/evidence. No errors, automatic inputs,
saves, reloads after startup or closure. Helper is idle awaiting human acknowledgement.

All84files in four complete original/portable save/state roots verified against manifest;
configuration snapshot and manifest digest independently checked. Both baseline observations
passed source/cache/object coverage and stable signature gates, decoded26objects on24x34map,
and confirmed G00 mech217/pilot242 HP5000 EN121 SP55. Source/snapshot/archive preservation
checks passed inside the handoff. No representative transition has been tested yet.

NEXT USER ACTION: open Z Gundam Unit tab and provide a fresh screenshot; do not transform
before observationA. No repeated G00/Shenlong screenshots. RequestA must use trial ID above,
sequence2, visible_form122 (confirm fresh screen), fresh timezone-aware screen_timestamp,
screen_path and explicit user_acknowledged. The helper only accepts frames acknowledged
within5minutes of request submission and after startup. Human game inputs remain exclusively
with user. Optional B-diagnostic disabled; after stableA ask for visible no-cost transform
and B-info screen, then eligible no-cost return and A-return. Inspect selector-pair deltas
manually before acceptance. If helper has exited or reads_disabled exists, do not reconnect,
replay, close or reload. Preserve session and report current state. Do not start another
emulator or another controller while this session remains open.

## Observation A corroborated — 16 October 2026

Existing owned trial collected request2/A from the user's fresh Z Gundam Unit-tab screenshot
(screen-002-A.png, private). Two separate paused observations agreed: mech122, pilot134,
HP4700/4700, EN128/170, SP24; selected actor152830640/object149303912. All26candidate objects
have one representative, source recipe equals cache, selected Info matches representative,
and normal-running checks plus source/snapshot/archive preservation checks passed.
observation-002.json and request-002.json exist; no disabled/error record. Helper remains
idle, emulator open; no automated game input or new save/load. Next request is3/B-info.

Ask user to return to map and inspect Z Gundam's visible Transform/Change command. Only if
visibly available with no cost, perform one form change and open new Unit tab/supply fresh
screen. If command unavailable/has cost or anything unexpected appears, stop and provide
menu screen instead. Do not infer availability from earlier VR marker. Expected mech123;
validate actual screen and resources before request3. No pre-Info diagnostic sample.

## Observation B-info corroborated — 16 October 2026

User supplied Waverider Unit screen with Kamille HP4700 EN128 SP24. Existing owned helper
request3/B-info passed two separate observations, normal-running, structural, continuity and
source/snapshot/archive preservation checks. Selected mech122->123, pilot134 unchanged,
actor152830640->152830656, SAME object149303912. HP4700/4700 EN128/170 SP24 unchanged.
All26objects, tile geometry and every nonchosen representative binding unchanged. Source
actor list unchanged; cache removed only prior actor and added only transformed actor.
Selector pair index2 changed exactly[122,134]->[123,134]; all89other pairs unchanged. This
corroborates the decoded form-selector update for this one human transformation, not a
universal cross-stage or crew-assignment claim. Raw evidence/screens remain private.

observation-003.json and request-003.json exist, no disabled/error record; helper idle,
emulator open, no assistant game inputs. NEXT: user returns to map, uses visibly available
no-cost reverse transformation, opens Z Gundam Unit tab and provides fresh screenshot. Only
then publish request4/A-return with visible_form122. If reverse unavailable/cost/unknown,
stop and retain partial coverage; do not reload/replay/recover automatically.

## User-requested form-stat comparison — 16 October 2026

Offline comparison of the already captured A/B-info spans confirms selected mech-record
DEF(u16+0A)1000->900 and MOB(u16+08)115->125, with HIT(u16+06)145 unchanged, in both observations
of each phase. Byte+05 is6->8, matching visible MV in this pair; retain as newly corroborated
movement candidate, not universal legality/reachability/movement-budget contract. Selected
record changes08E91CB0->08E91D00 alongside mechID122->123. Both form records already contain
their respective MV/DEF/MOB values in both before/after samples: the selected form switches
between existing records, rather than proving those bytes were rewritten during transform.
Name text is not decoded:122/123 are associated with user-visible Z Gundam/Waverider labels.
Private reproducible numeric summary form-stat-comparison.json. No live reads, input, backup
or helper changes needed. Await fresh reverse-form screen for request4/A-return as above.

## Scoped trial complete — 16 October 2026

Request4/A-return passed both observations and all preservation/continuity gates.
The complete decoded stable signature equals initialA. Selector pair2 restored
[123,134]->[122,134]; all other pairs, all26objects and positions unchanged. Selected
actor/object/pilot/form/resources restored; MV/DEF/MOB6/1000/115 match fresh returned
screen. Private transition-acceptance.json records the comparisons. Independent research
summary: docs/research/2026-10-16-representative-transition-validation.md.

All live phases baseline/A/B-info/A-return completed. Optional diagnostic timing remains
unavailable by design. No more requests are accepted by the completed handoff phase;
helper remains idle, owned emulatorPID14684 open. Do not close, reload, reconnect or
start another trial automatically. No further screenshot needed for this research.
The entire battle programme is NOT complete: next dependent work is a written offline
representative-inspection contract/design, not an autonomous runtime promotion.

Independent final evidence review confirmed all six188156-byte observations, complete
26object coverage, exact pair2 change/return, unchanged other bindings/source/geometry,
identical returned stable signature, numeric stats and84save/state+2configuration file
manifest counts. No material corrections. Research summary and main evidence summary
updated; no production changes or new live operations. Next: prepare offline representative
inspection design for review; preserve the existing open session and completed helper.

## Next production extension prepared — 16 October 2026

Proposed representative-inspection design and implementation plan written under
specs/2026-10-16-representative-inspection-design.md and
plans/2026-10-16-representative-inspection.md. User written review remains required before
production code, as AGENTS.md specifies; trial approval does not silently extend to the
new reader. Independent spec review corrected exclusion/duplicate ordering and clarified
ID bounds, capture scope and overlap rules. No new code/game operations. On approval,
execute bounded core and IO tasks with TDD, preserve existing uncommitted changes and
perform private offline evidence/CLI verification. Do not restart the completed trial.
