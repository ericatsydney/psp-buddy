# Protected Move/Attack trial evidence and stop — 17 October 2026

The user approved session testing without repeated approval requests. Trial
20261017T042410268772Z-4a4060ede78e429b9ed0fba5a2da2e0a used fresh complete original/
portable save snapshots and configuration backups, all SHA-256 verified. Human supplied
all navigation and one Move. No assistant game-input, combat, Standby, End Turn or save
command was sent. PPSSPP stays open; no reload, closure or reconnect is authorized by a
failed read.

## Accepted observations

Two separately paused stable samples at each accepted stage, 188956 bytes/63 reads each:

| Stage | Z tile | HP | EN | SP | Two-bit counter | Unmoved count |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Unit baseline | (18,13) | 4700 | 128 | 24 | 1 | 20 |
| Move preview | (18,13) | 4700 | 128 | 24 | 1 | 20 |
| Post-Move Attack/Standby menu | (14,15) | 4700 | 122 | 24 | 1 | 20 |

Only Z's direct tiles and EN changed among all26 representative rows. The red overlay
was explicitly confirmed by the human as Move range. This demonstrates post-Move Attack
availability for this unit/state, not universal action legality or an EN cost formula.
Movement may still be provisional until Attack/Standby completes; no cancellation tested.

The first weapon page showed GrenadeLauncher greyed out and VulcanCannon, BeamRifle,
BeamSaber and BeamConfuse highlighted. User confirms unavailable entries greyed and there
is a second page. Page2 and the memory availability predicate remain unverified.

## Battle preview and read failure

Human selected BeamRifle against Taurus HP4104/6600, EN50/120. Forecast showed Z HP4700,
EN122, hit93%; enemy BeamCannon counter hit65%. A second Taurus HP2603 was displayed as
support defender. Its possible damage/defeat would require explicit explanation rather
than attributing every enemy change to the primary target. No combat confirmation received.

At sequence5 attack-preview, collection stopped at exact fingerprint comparison with
ValueError: code/patch identity anchor mismatch. The helper disabled further reads and
left PPSSPP open. Exact failing address/bytes were not logged by that version, so the
root cause is unresolved. All26 anchor windows match across the four previous successful
stages; game/emulator identity passed before the failed fingerprint loop. Failure occurred
after weapon selection at battle preview; the evidence cannot pinpoint when bytes changed.
Do not assume an overlay or relax/remove an anchor based on this temporal association.

Private evidence: local/move-attack-trial-20261017/active-run.json points at the run;
its disabled.json, request.json and screenshots are preserved. Failed request must not
be replayed. No new emulator reads are permitted by the disabled helper. Offline diagnostic
logging improvement is being tested; it does not alter this running session or re-enable it.

## Next work

Preserve the current forecast and unsaved move. Do not press Start for this test while the
reader is unverified. Improve error address/hash reporting offline, review and document
any new diagnostic capture boundary before using it; current data cannot prove which
anchor changed. Counter consumption after Attack, weapon-list memory fields and broad
legality remain pending. Never claim completed battle acceptance from this partial trial.

Offline diagnostic correction complete: two tests failed before the change, then40
collector tests passed, Ruff and mypy passed. Anchor errors now name address,size and
expected/observed SHA256 from bytes already read; no extra live reads, weaker check or
raw-byte leak. Independent review cleared. Running disabled helper is unchanged and
no request replay/reconnect was attempted. Original SAVEDATA and PPSSPP_STATE hashes
still match the fresh trial manifest after the stop.

## Second visual forecast, Euclid

User backed out and selected BeamRifle against Euclid; fresh screenshot
4bacc0ee-e653-475d-8c00-1d4bb07e958b shows targetHP5211/9600 EN89/150,
ZHP4700/4700 EN122/170 anddisplayedammo9. Hit97%versusEuclidcounter49%
(HiEnergyBeamGun). SameTaurusHP2603 supportdefenderSDef1/1 remainsvisible.
Thisisvisual-onlyevidence;disabledhelpernotreenabled,newmemoryrequestnotpublished,
noStartconfirmationreceived. Differenttargetforecastdoesnotresolvefingerprintfailure.
Privatecopyandmetadataretained; noassistantgameinput/reload/close.

## Unconfirmed protocol lead for diagnostic replay

Official pinned PPSSPPv1.20.4 source,
https://github.com/hrydgard/ppsspp/blob/v1.20.4/Core/Debugger/WebSocket/MemorySubscriber.cpp,
shows memory.read defaults replacements=true. The false option temporarily clears
replacement/JIT emuhack operations for the read and restores them afterward. Our protected
adapter explicitly permits only replacements=true. This suggests a possible difference
between runtime instruction representation and retained fingerprints, but does NOT
identify the failed anchor or establish the cause. Do not modify that protocol guard or
relax comparisons on this hypothesis. First capture exact failed bytes with the approved
forensic replay; any supported read-mode change needs separate evidence, tests and review.

## Failure reproduced and classified: runtime JIT markers

Ready-enabledtrial064129203735Z sequence5 repeatedfailureat0x088A2AAC,size64.
Forensicartifactretainsbefore/afterbytesprivate. Onlytwo4-bytewordsdiffer:
088A2AAC original8C82000C→680BF4BA;088A2ABC original3C0208E5→680BF506.
Remaining56bytesexactmatch. Bothobservedwords satisfy PPSSPPv1.20.4
MIPS_IS_RUNBLOCK(word): (word&FF000000)==68000000. Official definitions:
https://github.com/hrydgard/ppsspp/blob/v1.20.4/Core/MIPS/MIPS.h .
PinnedMemorySubscriber.cpp documentsmemory.read replacements=false and its
SaveAndClearEmuHackOps/RestoreSavedEmuHackOps scope. Existingadapteralwaysrequests
replacements=true, so runtimeJIT words enteredcodefingerprintcomparison.
ThisidentifiesthecapturedmismatchasJITinstrumentation; itdoesnotprovethatallother
forecast-memoryfieldsarevalid. Do notmaskarbitrarywordsorremovefingerprints.
Correctfix: dedicatedboundedoriginal-codeviewinsideownedpausedobservation, exact
comparisonretained, ordinarydatareadsunchanged, publicgenericfalsemodeprohibited.
Currenthelperremainsdisabled; noStart/reconnect/replay. Freshprotectedlivevalidation
neededaftercode-readfixandreview. Noactualattackorcounterconsumptiontestcomplete.


## Original-code fix passes protected live forecast

Fresh trial 20261017T094104744558Z-cf11a0f902ff4c4abf16599411152e48,
PPSSPP PID11364, verified all four complete save snapshots and configuration
backups before launch. The user closed the previous window normally. New helper
sequence2 confirmed selected Z Gundam, HP4700 EN128 at(18,13). Sequence3 captured
the actual unconfirmed destination preview: resources and tile unchanged.
Sequence4 after human Move confirmed tile(14,15), EN122, HP4700, SP24, counter1.
Sequence5 at BeamRifle/Euclid forecast passes all exact code fingerprints and
structural checks in two stable paused observations. The prior JIT-related failure
does not reproduce using the dedicated original-instruction view.

Fresh user forecast image shows Z4700/4700 EN122/170, BeamRifle97%, ammo9;
Euclid5211/9600 EN89/150, HiEnergyBeamGun49%; Taurus2603 SDef1/1.
Memory corroborates Z resources/tile, Euclid object149302768 at(12,17), and support
Taurus object149301208 HP2603 EN49 at(12,16). Hit chances, weapon availability and
ammo are visual evidence only; this reader does not decode those fields.
No Start/combat has yet been confirmed. Next authorized step is one human Start,
then two post-combat observations, without EndTurn/save/reload or other commands.


## First human Move/Attack trial: post-combat capture passes

User confirmed Start once and replied ready at the returned map. Sequence6 has two
stable, structurally valid observations with all exact canonical fingerprints passing.
Z Gundam HP4700->1119 (3581 damage), EN122 unchanged, tile(14,15), SP24.
Support Taurus HP2603->450 (2153 damage), EN49 unchanged. Main Euclid HP5211
unchanged, EN89->74 (15 spent). These are observed resource deltas, consistent
with support defense intercepting the attack and Euclid counterattacking; damage
prediction and hit/miss decoding are not implemented. All26 representatives remain.

IMPORTANT LIMITATION: Z counter_value remains1, counted_as_unmoved remains true,
and displayed aggregate remains20 after actual combat. This does not establish
post-attack action availability. Do not promote this counter or aggregate into a
can_act flag, turn-completion decision or live capability. Need a fresh independent
visual/action-state observation and dedicated action-state research before autonomous
unit selection. No further action, EndTurn, save or reload has been requested.


## Offline action-status candidates after user confirms greyed Z

User independently confirms Z Gundam is greyed out and cannot open its command
menu after combat. Compared retained captures1..6 with both samples of each
before/after pair; no new emulator reads or controls performed.
Z object0x08E63268 offset0x25 is 0A at baseline/unit/move-preview,08 after Move
and at forecast,60 after combat. This packed status byte distinguishes these
observed phases; semantic bit meanings remain unproven. Offset0x60 is40 for all
five precombat stages,00 after combat. Offset0x62 remains01 throughout, explaining
why the existing EndPhase counter did not reflect exhausted action availability.
Offset0x38 is00 until forecast,01 at forecast,00 after: transient combat-state
candidate rather than persistent action availability. Offset0x37 also changes,
but is not assigned semantics.

Across26 representatives, Z is the ONLY object whose0x25 or0x60 changes between
forecast and postcombat. Other allies with status0A/08 retain0x60=40; existing
status60 allies and all five Foes have0x60=00. Other allied values02/04/05 also
have0x60=00, so absence alone cannot be interpreted as 'already acted' across
all deployment/carrier forms. Third-party Wing Zero has0A/40, demonstrating that
this candidate must be combined with independently verified affiliation.
Strong candidate: per-object action status at+0x25 and/or+0x60, separate from
+0x62 counter. Not yet an authoritative can_act mapping; requires unused-ally
command availability corroboration and code-consumer/independent transition
validation before enabling autonomous selection. Production behavior unchanged.


## Destiny independent unused-ally corroboration

User opened Destiny Gundam command menu and reported Move, Attack, Spirit, Info;
then Info HP5200 EN230. Exactly one retained post-combat representative matches:
object149303288 (0x08E62FF8), mech197/pilot208, rawgroup0, tile(19,5).
Its retained status+0x25=0A and candidate+0x60=40, unchanged across all six trial
stages; finished Z has60/00. This is independent human menu/resource corroboration
against retained memory, NOT a fresh selected-Info memory capture. No new reads,
inputs or emulator state changes by assistant. Candidate semantics still provisional:
needs consumer-code/second transition validation; no production can_act enabled.


## Static candidate trace: bounded result, not yet a defining command path

Scanned retained clean instructions for byte/halfword/word references to candidate
object offsets and retained private disassembly under local/action-status-trace-20261017.
The object resolver is code-backed: actor+0x0C through0x08923EF8/0x0894C560.
However, matching instruction offsets alone do not prove the base pointer is this
object. For example0x08861558 writes destination+0x60 by copying source+0x20;
0x0883BEC8 decrements a+0x25 field in a state-machine structure. Neither path has
been linked to the selected actor's object; they cannot establish action semantics.
Other +0x60 accesses read pointers in unrelated tables. Thus no can_act predicate
or exact command-menu/grey-render consumer is proven by this bounded trace.
Empirical0A/40 versus60/00 remains a candidate only, supported by Z/Destiny human
observations. Next trace must follow the command-menu eligibility/grey-render call
path back to an actor-resolved object, rather than infer from matching offsets.

Correction to earlier shorthand: the established two-bit EndPhase counter is at
object+0x08 bits3..4. The separately observed unchanged byte+0x62 is NOT that
counter. The actual decoded counter_value1 remained unchanged independently.
No new emulator reads, inputs, state changes, or production code were performed.


## User-provided infinite-movement cheat decodes to object+8

Code D0000002/10001000 conditions the next three code lines on Triangle.
80661F58/00630068 with0000000C/00000000 is byte multiwrite: starting
PSP0x08E61F58,99 entries,stride0x68(104),value0x0C,no value increment.
Confirmed type8 and joker decoding in pinned PPSSPP Core/CwCheat.cpp v1.20.4:
https://github.com/hrydgard/ppsspp/blob/v1.20.4/Core/CwCheat.cpp .
All26 retained representative object+8 addresses align exactly with this99-slot
sequence. Z object0x08E63268 ->target0x08E63270,index47; Destiny0x08E62FF8
->target0x08E63000,index41. Thus the cheat targets the same byte as the previously
traced two-bit counter, not candidate+0x25/+0x60. Value0x0C sets bit2 and bit3,
clears other bits; it simultaneously changes multiple state bits. Its label alone
cannot establish which bit restores command availability. In retained captures
Z byte+8 AC baseline,8C aftermove and aftercombat; Destiny also AC->8C.
Both retain(counter>>3)&3=1. Need trace individual masks/setters/command consumers
of this byte. Do not infer counter alone or previous candidate bytes are can_act.
No cheat enabled or memory changed. Exact slot alignment verified offline.


## Second user cheat: address does not match an action consumer in retained build

User supplied201594F4/00000000 labelled Infinite Action Always. Type2 writes
32-bit zero (MIPS nop) at0x089594F4. Both original and portable retained clean RAM
contain8C44859C there: lw a0,-0x7A64(v0), the delay slot of jal0x0882C77C.
Surrounding function parses/formats character pairs then calls0x0882B9E4 with
screen-like coordinates and color-setting calls. No actor/object action-state write
is established at this address. This is incompatible with treating the label as a
verified patch for this retained English-v0.8/v1.01 image; different game/version
or code transcription remains possible, not proven. Do not apply it. Need the
source game's _S identifier and game/patch version or original reference link.
No emulator memory/input/config changed. Exact instruction/window retained private.


## Byte+8 bit5: mode-specific selection path traced

Independent offline trace establishes0x088AB6D8(tilex,tiley) ->grid0x08E52A98,
row lookup0x0883F100 ->actor->u32(actor+12) ->extract(objectbyte8>>5)&1 at
0x088AB714..720. Returns actor only if bit5 set. Static JAL caller0x088E5E2C
stores result at UI+0x7C, conditional on map handler mode value2.
Same handler uses unfiltered0x0883BD48 on cursor tile change0x088E5D00 and stores
actor0x088E5D08. Thus bit5 does not gate every selection mode. Separate0x088A7F60
iteration uses same bit to set low nibble object+0x38 to0/1. Relevant five windows
match exactly in original and portable retained clean RAM.
This explains why bit5 can clear while Destiny still offers Move/Attack. Does not
prove finished action, grey rendering or command eligibility. No can_act enabled.
Private agent trace output retains defining instructions and hashes.
