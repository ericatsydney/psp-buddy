# Destiny diagnostic helper plan

Scope authorized by the user's explicit Move/Standby test and existing session
approval. Design self-review: state order, byte provenance, unchanged roster guards,
no current-session hotpatch/attach, and fresh-launch protection explicitly specified.

1. Private local/move-attack-trial-20261017/standby_handoff.py and test_standby.py:
   write meaningful RED tests first for ordered separate stages and unsafe transitions,
   implement subclass using existing Handoff validation/collector, no game inputs.
2. Minimal startup dependency injection in existing handoff.main/startup_session to
   permit a statically selected diagnostic Handoff class, with defaults unchanged.
   Test injection before changing production helper; no runtime monkey-patching.
3. Run .venv/Scripts/python.exe -m pytest local/move-attack-trial-20261017
   --basetemp local/pytest-destiny-standby-final -p no:cacheprovider -q.
   Run Ruff private folder; source suite if production src changes (none planned).
4. Independent review, fix findings and rerun affected tests. Record results.
5. Preserve open window until normal human close; then fresh verified full backups
   and dedicated launch. Collect Info/preview/move/standby in order, each fresh ready.
   No need to replay Z attack. Never claim existing highlighted preview captured.


## Implementation and verification

Dedicated standby_handoff.py and28 diagnostic tests implemented TDD. Minimal
handoff.main/startup_session handoff_type dependency injection defaults unchanged;
entrypoint statically selects StandbyHandoff, no runtime hotpatch/attach.
Root final verification:149 private helper tests passed in5.82s; Ruff entire private
folder passes. Meaningful RED observed for missingmodule, DI selection, persistence
failure-latch and initial dead-ally guards before implementation/fix. Independent
review found two important issues (postprocessing persistence not latched; initial
allies-alive incomplete); both fixed with RED/GREEN regression tests. Final review
of those fixes pending. No production source modules changed in this task; earlier
1092 source/scenario tests passed before helper-only extension.

Open PPSSPP PID11364 remains untouched at user's Destiny Move preview. That
preview was NOT captured, original helper has finished its approved state machine.
Cannot use newly written code in existing process. Next step once review clears:
request normal human close, handle warnings preserving user changes, then fresh
all-four save snapshots plus original/portable configs and slot2 startup using
standby_handoff.py. No repeated Z combat required. No automatic close/load/save,
new trial or command until operational gate. No commit.

Final independent review cleared both fixes with no remaining findings. Ready for protected fresh trial; current window still unchanged.
