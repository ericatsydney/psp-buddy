# Manual ready checkpoint helper update

User requested ready instead of repeated images; prior sessiontesting approval applies.
Write only ignoredhandoff.py/test_handoff.py, no productionAPI oradapterchanges.

- [x] TDD: ready-onlyUnit/Move/postMove valid; stale/naive/future/nonmonotonicack rejects;
  image/ackmix rejects; attack-previewackonly rejects; requiredstageandsafeacks remain.
- [x] Implement exact evidence_mode=human_ack schema for nonforecaststages, acktext/time
  validation and explicitreportmodality. Legacy image-mode unchanged. Unitackrequires
  corroboratedselectedInfo/currentbinding matching rowinboth separatelypausedreads.
- [x] Focused+retainedintegration suite, Ruff, independent review; preserve evidence logs.
- [x] Activate only via freshbackup/startup; do nothotpatcholdprocess, createfalseframes,
  bypassrequiredforecastimage or reusescreens. CurrentZUnitbaselinewaiting; leaveopen
  untilrestartstep. No additionalapprovalwithin sessiontesting, but no warningdismissal.

90privatehelper/retainedintegrationtests pass; Ruff andcollectorstrictmypy pass.
Independent review cleared; provenance accuratelydistinguishes UnitInfo versus
postmoveboundrow, andpartialstopdoesnotclaimmemorycaptures. Unitackusesexpected_*
keysinsteadofvisible_*; resourcesareexpectedbaseline/currentmemory,notclaimedvisual.
Currentoldemulatorclosednormally; process/listenerinventoryempty. NewhelperPID3492
run20261017T1641240506 preparingfreshverifiedbackupsbeforestartup. No live capture
wasfakedorpostedtotheoldimage-onlyhelper; userwillneedfreshreadyafternewstartup.

Activatedfreshtrial20261017T064129203735Z-5795cf645640473c9bf11eb25ea84e52;
PPSSPPPID4496,helperPID3492,active-run20261017T1641240506. Fourfullsavebackups
andportableconfig independentlySHA256verified;originalSYSTEMbackup064123Z.
Slot2knownG00baselinepassedtwice,helperidle,nextseq2. Usermustsendfreshready
afteropeningZUnitnow; earlierreadybelongsoldsessionandwasnotreplayed.
HumanackUnitrequestusesexpected_mech_id122,pilot134,HP4700,EN128,object149303912,
corroboratedInfo+rowinbothsamples. Noimagefieldorfakeframe. Forecastimage remains
mandatory; sameMove/Attackoneunit scope, no automaticgameinputs.
