# Approved protected Move/Attack trial plan

User approved written design and all planned testing this session. No repeated permission
questions. Human gameplay acknowledgements still gate each step. No commits.

- [x] Collector task: new ignored local/move-attack-trial-20261017/collector.py and
  test_collector.py. Reuse prior validated bounded collector mechanics but stale Info
  must not control postmove/combat. TDD fake/readretained spans; all current representative
  object stats/tiles/counters/groups must enter stable signature. Baseline optional Info
  validated when supplied; record stale globals separately.1MiB/64KiB bounds and pause gates.
- [x] Handoff task: new handoff.py/test_handoff.py in same ignored directory. Reuse reviewed
  no-close startup/backup/session ownership; state baseline→unit-baseline→move-preview→
  post-move→attack-preview→post-combat, plus explicit partial stop whenattackabsent. Human
  ack/stage/sequence/trial validation; two stable observations; no form/resource equality
  assumptions after movement/combat. Bind chosen object/unit atbaseline; preserve unrelated
  identities beforecombat, permitvalidatedfoedefeat rosterchangeafter. No auto inputs.
- [x] Root integration/review: fake/retained integration tests, Ruff, existing backup/launch/
  debuggertests. Independent safety review and fixes before startup. Use unique local
  basetemp, .venv/Scripts/python.exe. Never launch from failing/uncertain checks.
- [x] Preflight: fresh process/listener/pathinventory, verify sourcesnonwriting, quota>=10%
  remaining. Helper Launcher.prepare creates completeoriginal+portable saves/configSHA256
  snapshots and manifest; inspectpreparedreceipt. Isolatedslot2startonly, authenticate
  ownedlistener/identity, baselineknownG00HP5000EN121SP55. Neverclose/reloadexistingwindow.
- [ ] ReportreadyPID/trial/backupverification and requestchosenallyUnit screen. CaptureA
  onlyafterhumanready. Move/Attackperformedbyhuman, assistantrequestsconcretescreensand
  observationsinapprovedorder. No elapsedtimeasack. Preserveopenstateonfailure/absence.
- [ ] Recordbaseline/postmove/postcombatcounter/tile/resources andvisiblecommand evidence;
  partial coverage explicit. No generallegal-actionorautonomyactivation. Archivehandover,
  originalhashchecks, noautomaticclosureorrollback.

## Protected startup complete

61newprivatehelper tests and93existingbackup/launch/debuggertests pass; Ruff+collectormypy
pass. Independentsafetyreview clearedaftercausality/freshframe/livingfoe/safe-statefixes.
Freshcompletefour-source save snapshots+portableconfig independentlySHA256verified;
originalSYSTEM separatelyfreshverified underbackups/move-attack-original-config-* .
Trial20261017T013752523726Z-669de784530e49d2b1d38cd21e1e6cc2;PPSSPPPID15276;helperPID11324.
G00baselineHP5000EN121SP55 matches two separatelypausedcaptures; helperidle,sequence2next.
Activepaths:local/move-attack-trial-20261017/active-run.json andrecordedevidence/ready.json.
Userapprovedallplannedtestingthissession; nofurtherpermissionrequests. Nextaskforfresh
Z GundamUnit-tab screenshot/ready,bindobjectfromcurrentrows thenpublishunit-baseline
requestwithexplicitactualhumanack. Do notMoveuntilmove-previewrecordandhumanconfirmation.
NoMove/Attack/EndTurn/save/rollbackinputsent; leavewindowopenandhelperidlewhileuserabsent.

## Heartbeat state verification — 17 October 2026,12:54AEST

Read-only process/listener inventory now shows no PPSSPP process, no prior helper
PID11324/child and no27312listener. Exit cause unknown; no assistant close/kill/reload
was issued. Evidence remains baseline observation001 only; no human Unit screenshot
or Move/Attack acknowledgement received. Do not claim the trial is still open.
Original SAVEDATA/PPSSPP_STATE and allfour immutable snapshots independently SHA256
match startupmanifest. No restart/gameinput done on this heartbeat. Preserve writable
runtime changes; freshbackup+startupchecks required before a later approved restart.
Session testing approval persists; do not ask repeated permission. Resume when user
returns for the human-assisted steps. No repeated fieldresearch or completedcodechanges.

## Approved restart after usage reset — 17 October 2026,14:29AEST

User resetusage;primary/secondary0%usedverifiedbeforestartup. NoexistingPPSSPP/listener.
FreshoriginalSYSTEMbackup and allfourcomplete save snapshots+portableconfig verified
SHA256. Newtrial20261017T042410268772Z-4a4060ede78e429b9ed0fba5a2da2e0a;helperPID10276,
PPSSPPPID7776. Bothbaselinecapturespassed G00HP5000EN121SP55. Helperidle,nextsequence2;
active-run.json pointsnewrun-20261017T1424048261/evidence, earliertrialevidencepreserved.
Next human step: fresh Z GundamUnit-tab screenshot, beforeanyMove/Attack. Sessiontesting
approvalpersists; do not ask again. NoMove/Attack/EndTurn/saveinputsent.

## Human Z Unit baseline captured

Fresh userscreenshotcodex-clipboard-0c329580-95f2-4f49-a8d5-7aa8cd34d81d.png
corroboratesZ Gundam/Kamille HP4700 EN128 SP24. Currenttrialsequence2 stabletwo
observationspassed,object149303912 actor152830640 mech122 pilot134 tile(18,13),
counter1,unmovedcount20. SelectedInfocurrentbindingcorroboratesbaselineonly.
Nextsequence3 move-preview: humanopenMove/highlightlegalemptydestination andsend
freshscreen BEFOREconfirmingMove. Needrecordexactdestinationfromcurrentevidence;
do notguesslegalityfromMV6orcounter1. NoMove/Attackinputconfirmedorsent.

## Move preview recorded

User supplied current map screenshot3cc84824-32e2-41bf-b0f8-e53b4ef25031 and explicitly
confirmed red overlay is Move range. Screen grid anchored by known Z(18,13) and
Taurus(12,15)/(12,16) places highlighted destination(14,15), empty and within shown
Move overlay. Observation003 two stable reads: Z still(18,13),HP4700EN128SP24counter1,
unmoved20. No assistant gameplay input. NexthumanconfirmMoveonce andsendresulting
commandmenu WITHOUTAttack/Wait/EndTurnoropeningInfo. Postmove sequence4requiresfresh
screen,safeplayerstate,visibleAttackavailability andobservedtile(14,15); provisional
movement recorded explicitly rather than assumedspentcounter.

## Human post-Move command menu captured

UserconfirmedoneMovebyshowingfreshcommandmenu5524557a-f8bb-4f05-a0c9-c607558181c4
withAttack/Standby. Observation004stabletwo captures: Ztile18,13→14,15;EN128→122;
HP4700/SP24/counter1unchanged;unmovedcount20unchanged. Provisionalstatusrecorded,
noStandby/Attack/combatconfirmed. Exactall-rowcomparisonstoredprivateevidence.
NexthumanselectAttackandsendweaponlist;chooselegalpost-MovenonMAPweaponthenliving
Tauruspreviewbeforecombat. Noadditionalapprovalquestion; waitactualhumansteps.

## Sequence5 failed fingerprint — preserve open forecast

See research/2026-10-17-move-attack-trial.md. Atattack-preview helperdisabledwith
code/patchidentityanchormismatch, exactaddressnotlogged. Noattackconfirmed. Original
windowPID7776 leftopen;helper10276remainsdisabled,no reconnect/replay. Lastaccepted
sequence4 Move→(14,15),EN122,counter1,unmoved20. Failedsequence5requestmustnotreplay.
Offlinechecksall26fingerprintwindows matchacceptedstages1..4; failingbytesunavailable,
rootcauseunknown. Nextimprovedofflineerrorlogging,thenrevieweddiagnosticboundarybefore
newliveevidence. Do notautoStart/reload/closeuserstate. Sessionapprovalpersists.

## Explicit diagnostic restart authorized

Userrequestedrestarttoreplicateandtestagain. NormalCloseMainWindow requestedonlyowned
PID7776; itremainedrunning, userhandlednormalcloseandrepliedclosed. Follow-upinventory
showsnoPPSSPP/no27312listener. No forcekillorwarningdismissalissued. Currentprovisional
moveisresetonexplicitlyrequestedslot2restart; ondiskcopiespreservedbynewfreshbackup.
63helpertests passwithnormalfilesystemaccess (sandboxpytesttemporarydirectorydenied,
notfunctionalregression); Ruff/collectormypypass. Beforelaunchprivateforensiclogging
willpreserveonlyfailingalready-readboundedanchorwindow+address/hashes, acceptance
remainsrejected/disabled. TDD+independentsafetyreviewbeforefreshbackups/startup.
Allsessiontestingapprovalpersists; do notaskagain. NextbaselineUnit/Move/forecast
stepsremainhuman-controlledwithfreshscreens; noautomatedbattleinputs.

## Forensic diagnostic replay prepared

75privatecollector/handoff/integrationtests pass;Ruffpasses;collectorstrictmypypasses.
Privatehandoff retains existingdynamic-import/untypedbase typinglimitations; no claim
ofstrictmypycleanforit. Independentsafetyreviewclearedincludingartifactwritefailure
regressions. Exactcomparisonunchanged; privatefailingwindowartifactvalidatesknown
anchor,bounds<=4096,hexlengthsandhashes; noextraread/retry/acceptance.
Userclosedownedoldemulatornormally; newhelperPID17860run20261017T1629543610preparing
freshsnapshot. Helper/configSHA256recordedrun/reviewed-helper-sha256.json. Do not
reuseoldscreensorfailedrequest. WaitfreshreadybaselinebeforehumanMove/Attacksteps.

## Forensic replay ready — 17 October 2026,16:33AEST

Freshtrial20261017T063000019725Z-debd9a6031f34a8898e5260b2e08c075 active.
PPSSPPPID12292,helperPID17860;active-runnewrun20261017T1629543610. Fourcomplete
savesnapshots+portableSYSTEM independentlyverifiedSHA256;originalSYSTEMfreshbackup
062927Z preserved. Slot2baselineG00HP5000EN121SP55passedtwice;helperidle,nextseq2.
Reviewedboundedforensicloggingloaded (run/reviewed-helper-sha256.json). NoMove/Attack
inputsent. NextfreshZUnitscreen→sameMove(14,15)→postMove→BeamRifleEuclidforecast,
withcurrenthumanack/screensateachstage. Onfailurepreserveanchor-mismatch.json,
remainfailclosed, noStart/reconnect/replay. Noadditionalapprovalquestions.

## Ready checkpoint workflow now active

Userrequestedreadyinsteadrepeatedscreens; reviewedupdate90tests/Ruff/collectormypy
passes. Newfreshtrial064129203735Z-5795cf645640473c9bf11eb25ea84e52 PID4496/helper3492
loadedslot2,backupsverifiedandbaselinepasses. active-run.json updated. Nextseq2
freshZUnitready(withoutimage), expected-ID/resourcefieldscheckedagainstcurrentInfo
andrepresentativerowinbothsamples. Do notreuseoldhumanack; helperpreservesreal
evidencemodality. Exactworkflowresultsin2026-10-17-ready-checkpoints.md.

Ready-enabledtrial: sequence2 human_ackUnitbaseline succeeded, noimage. Bothcaptures
currentInfo matches Zobject149303912/mech122/pilot134,HP4700EN128SP24,tile18,13,
counter1/unmoved20. Nextseq3 userhighlightssamelegalMove destination14,15 thenready;
no movementconfirmationuntilpreviewrecorded. Freshforecastimage remainsrequired.

Ready-enabledreplayseq3acceptedhumanconfirmed(14,15),BUTmemoryalreadyshowsZ14,15
EN122(counter1,HP4700SP24,unmoved20), ratherthanpremovetile18,13. Recordas
destination-readywithmovementalreadyreflected; no claimofpremovementpreviewinthis
replay. Do NOTinstructanotherMove. NextaskhumanwhetherAttack/Standbycommandmenu
isvisible,thenpublishpostMoveackseq4onlyafterconfirmation. All evidencepreserved.

## Reproduced failure: identified JIT marker false rejection

Currentready-enabledtrial064129...seq5failedat0x088A2AACsize64; forensicartifact
proves2changedinstructionwords680BF4BA/680BF506, bothPPSSPPv1.20.4RUNBLOCKmarkers,
56otherbytesunchanged. RawreadTrueincludesruntimeJITops. Exactpinnedsourcesand
comparisonrecordedresearch/2026-10-17-move-attack-trial.md. CurrentPID4496/helper3492
leftopenanddisabled; noStart/reconnect/replay. UserforecastEuclid5211,BeamRifle97%,
counter49%,supportTaurus2603unchanged. Next boundedadapterread_original_code fix
underownedpause; genericpublicfalse remainsrejected, exactfingerprintsnotmasked.
Spec/plan2026-10-17-original-code-read. Adaptertaskinprogress; privatecollector
integration/fullchecks/review/livevalidationremainpending. Stopsubstantialbelow10%
allowanceremaining; latest87%usedbeforeadaptercompletion. Preserveopenwindow.
