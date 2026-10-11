# Implementation and validation checkpoint

Date: 10 October 2026

## Verified foundations

The first implementation batch contains packaging/configuration and immutable contracts, the backup gate, pure policy/planning rules, and an offline debugger adapter. All changes remain uncommitted.

Final offline verification: **140 unit tests passed**, Ruff passed, strict mypy passed for eight source files, CLI help passed, and Git whitespace/exclusion checks passed. Tests use synthetic data. No scenario suite or live debugger test is implemented yet.

Independent reviews found and drove fixes for weapon-candidate duplication, combined attack movement, receipt expiry during verification, and queued input after uncertain transport. The final debugger concurrency and nested-control fixes were manually rechecked by the primary agent and covered by the passing regression suite. No known Critical or Important findings remain in the implemented offline scope; live acceptance remains incomplete.

Interpreter/dependencies: Python 3.14.3, pytest 9.1.1, Ruff 0.17.0, mypy 2.4.0, websockets 17.2. Installed dependency versions and red/green logs remain under ignored `local/`.

The production backup gate was also exercised while PPSSPP was closed. It verified 84 files across the complete original and portable SAVEDATA and PPSSPP_STATE directories, created separate preserved snapshots and writable copies, and successfully revalidated its single-use pre-launch receipt. The check did not launch/connect to PPSSPP or modify source saves. Its manifest remains under ignored `backups/verified-snapshots/`.

Snapshots are preserved by the runner and checked by hashes; they remain writable by their filesystem owner. No host ACLs were changed. Unsafe links/reparse points, including cloud placeholders, are rejected rather than silently skipped.

## Unverified live capabilities

| Capability | Evidence and remaining requirement |
| --- | --- |
| Trusted launch and connection | Live factory refuses before I/O. Bind the actual executable, game and effective writable memory stick to the current verified receipt before enabling it. |
| Debugger primitives | Synthetic ticket/event, timeout, cancellation, release and pause-preservation tests pass. Verify runtime schemas, identity and actual input outcomes in a newly protected trial. |
| Capture and recognition | Previous v1.20.4 capture attempts failed. A reliable current game frame and menu recognition remain unavailable. |
| Game profile and roster | No production layout is validated. Existing HP/EN candidates remain research evidence only. |
| Positions, resources and legal actions | Complete roster, affiliations, coordinates, max HP, EN, pilot stats/SP, healing, action status and weapon legality need visible correlation and reload checks. |
| Predictions and retreat safety | Validate combat previews and complete enemy attack footprints, including movement. Unknown evidence produces handover in the pure planner. |
| Defeat, departures and map clear | Require positive evidence distinguishing these conditions; no live detector exists yet. |
| Checkpoints, menu executor and supervisor | Not implemented or live-verified. Same-slot completion, save-before-end-turn, retry accounting and bounded menu flows remain planned. |

See [previous research](2026-10-10-hybrid-feasibility.md) for candidate addresses and prior user-confirmed input/save compatibility. This batch did not add a game observation or promote any candidate to validated profile data.

## Resume point

Tasks 1 and 5 are complete. Task 2's backup service and preservation checks are complete; the protected live connection fixture remains pending trusted launch integration. Task 3's offline primitives are complete; its live acceptance gate is unverified. Continue with protected launch/transport binding and then sequential capture/profile discovery before enabling menu automation. No autonomous battle or campaign progression is claimed.

## Continuation: 11 October 2026

The protected launcher and real WebSocket transport are now implemented and independently reviewed. The launcher backs up all four complete save directories and the complete portable configuration, copies the executable/assets into an isolated writable application, and consumes a fresh receipt before launching the selected slot. Process creation identity, exact command line and owned debugger listener bind a one-use connection session. The transport verifies a loopback peer, debugger subprotocol, emulator version and game identity before returning an adapter. Input, pause and resume recheck the launch binding; release cleanup remains available after uncertainty.

Normal inherited `CurrentDirectory` is rewritten only in the isolated configuration. Cheats, plugins, remote sharing and update checks are disabled there. Source configuration remains backed up and unchanged. PPSSPP v1.20.4 binds its HTTP listener to wildcard addresses, so owned wildcard listeners are accepted while the client endpoint and actual connected peer must be loopback. This is client connection validation; no host firewall rules were changed. The copied application uses no `installed.txt` and passes writable-directory probes to guard against PPSSPP's Documents fallback.

Verification before the discovery trial: **181 synthetic unit tests passed**, Ruff passed, strict mypy passed for nine source files, and CLI help passed. Independent review found no remaining Critical or Important findings in the launch/debugger boundary. Regression tests observed failures before fixes for inherited browsing paths, issuer bypass, failed-start cleanup, revoked controls, cleanup error masking, wildcard listeners and nonlocal peers. All changes remain uncommitted. Runtime capture and direct input outcome are still evidence gates.

Relevant upstream schemas: [Windows memory-stick initialization](https://github.com/hrydgard/ppsspp/blob/v1.20.4/Windows/main.cpp), [HTTP listener binding](https://github.com/hrydgard/ppsspp/blob/v1.20.4/Common/Net/HTTPServer.cpp), [input response after release](https://github.com/hrydgard/ppsspp/blob/v1.20.4/Core/Debugger/WebSocket/InputSubscriber.cpp), and [PNG capture while stepping](https://github.com/hrydgard/ppsspp/blob/v1.20.4/Core/Debugger/WebSocket/GPUBufferSubscriber.cpp).

### Protected observation trial

The first continuation trial created a fresh verified 84-file four-root save snapshot plus a complete configuration snapshot, launched the isolated OpenGL copy with the explicitly selected slot-2 state, and verified the owned listener, loopback peer, PPSSPP v1.20.4 and game ULJS00460 version 1.01. Both `gpu.buffer.screenshot` and `gpu.buffer.renderColor` returned `Could not download output`. The adapter stayed certain; the observed existing CPU/UI pause was preserved. Cleanup status was stepping=true, paused=true. No button press or save command was sent. The owned process was closed and all four source save inventories plus source configuration were verified unchanged.

Private evidence is in trial `20261010T205923530609Z-de6113f6ef244cbd98b5a7abbe8ad9f7` under ignored `backups/verified-snapshots/`, including the manifest, configuration manifest, copied application and capture result errors. The failed capture has not been promoted to a working capture method; loading a state and identifying its game do not by themselves prove a current visible battle frame.

An opt-in `tests/integration/test_debugger.py` now checks identity and pause preservation using a new protected launch for each invocation, with source verification in cleanup. Its opt-in-disabled skip and lint check passed; the module itself has not been run live. Direct cursor displacement, current capture and profile decoding remain unverified.

### Windows capture trial and current resume point

A second separately protected trial, `20261010T210324242695Z-10a9b13ce3be4d809688ab0577715b63`, again backed up the complete four save roots and portable configuration while PPSSPP was closed. It launched the isolated OpenGL copy for a bounded 60-second Windows observation window without connecting the debugger or sending inputs. The supported computer-use helper returned exactly one window belonging to the copied executable, titled PPSSPP v1.20.4 with game ID ULJS00460. Its screenshot/accessibility capture failed with `foreground window did not report a process id`. Refreshing the window inventory for the recovery attempt found that the bounded trial had already ended. No current frame was produced.

Both trials closed only their owned process and verified all source save/configuration hashes unchanged. No original restoration, cursor movement, save command or battle progression occurred. A Windows Security Alert was also present in the general window inventory; it was not opened or automated. The capture error does not establish whether the desktop was locked or whether a modal caused the problem.

Resume by investigating desktop/window capture availability in a **new freshly backed-up trial**. Do not reuse either completed trial as authorization. Reliable current, nonblank frames and visibly verified cursor displacement remain prerequisites for recognition/profile/menu work. Tasks 1 and 5 remain complete; Task 2's protected backup/launch/connection boundary is implemented and runtime identity-checked; Task 3's direct-input acceptance and Task 4 capture/profile validation are incomplete. The separate opt-in pause integration module is reviewed but not yet live-run. CLI execution remains fail-closed. Preserve quota headroom and continue with this evidence gate before additional tactical automation.

### Capture retries with user present

Further fresh protected Windows trials were attempted on 11 October. Trial `20261010T211117481794Z-dfd0ddd8d3f34c7e9e51d22b0439e593` activated the selected OpenGL window, but capture failed with `FrameArrived timed out: timed out waiting on channel`; refreshing and retrying returned `window capture timed out: timed out waiting on channel`.

The user then sat at the desktop to handle Windows prompts. OpenGL trial `20261011T033745914831Z-5258e77c90584728aca64e30d2f1af42` used a three-minute window. The helper again found and activated the exact isolated executable window, but both capture attempts timed out. The user explicitly confirmed that the game map was visible. This establishes manual visibility, not a working automated image source. The trial closed and source save/configuration hashes were unchanged.

A renderer comparison used trial `20261011T034404175558Z-f17ffcfd19ef4de4a4b6f6345a2807ed` with the copied original Direct3D11 setting, another fresh complete verified backup, and no game inputs. Both the initial and refreshed-window capture attempts returned `window capture timed out: timed out waiting on channel`. The same failure across OpenGL and Direct3D11 while the user could see the map suggests a Windows capture-helper/environment limitation; its root cause remains unproven. No Windows security request was automated or host security setting changed.

The Direct3D11 comparison also closed its owned process successfully and verified all four source save directories and source configuration unchanged. No automated current frame was obtained; capture remains the next implementation gate.

### User-provided firewall evidence

The user supplied a Windows Defender Firewall alert showing PPSSPP under the unique trial's `working/app/PPSSPPWindows64.exe` path and reported seeing the game inside the ChatGPT-controlled window frame. The prompt concerns network access, not permission to capture images. Windows application firewall rules use a full executable path; launching a copied executable from a new timestamped trial path explains why approval repeats. See [Microsoft's application-filter documentation](https://learn.microsoft.com/en-us/powershell/module/netsecurity/get-netfirewallapplicationfilter?view=windowsserver2022-ps).

This explains repeated prompts but does not establish the capture-timeout root cause: the owned loopback debugger connection worked, and Windows capture still timed out after the user handled prompts and confirmed a visible map. The next investigation should distinguish capture-session/frame-delivery problems from PPSSPP-specific capture behavior, before another renderer change. The ChatGPT window frame and manual map visibility alone do not prove the screenshot API delivered an image. No firewall rule or security setting was changed by the agent.

### Alternative capture paths researched

The official v1.20.4 Windows menu defines **Debugging → Take Screenshot**. Its handler calls `TakeUserScreenshot()`, which selects a free screenshot filename and schedules a PNG/JPG capture. The game-image mode selects `ScreenshotType::Display`, while output mode selects `ScreenshotType::Output`. This is a distinct request/scheduling path from the stepping-only WebSocket GPU-buffer commands and is the recommended next protected test. It may still share underlying graphics readback, so success is not assumed. Keep output in the isolated trial memory stick, require a newly created complete nonblank image, and compare two frames before relying on freshness. No save-state operation is needed.

Sources: [menu definition](https://github.com/hrydgard/ppsspp/blob/v1.20.4/Windows/ppsspp.rc), [menu handler](https://github.com/hrydgard/ppsspp/blob/v1.20.4/Windows/MainWindowMenu.cpp), and [scheduled user screenshot implementation](https://github.com/hrydgard/ppsspp/blob/v1.20.4/Core/Screenshot.cpp).

Windows [Desktop Duplication](https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/desktop-dup-api) is another API for acquiring desktop frames, distinct from the Windows.Graphics.Capture helper that timed out. It would need a separately validated integration and careful selection/cropping of the visible game region; overlapping windows can contaminate desktop images. Manual user screenshots can aid diagnosis but do not provide an autonomous capture loop. These alternatives were researched without launching PPSSPP or changing user data and remain unverified.

### Fixed MVP runtime selected by user (2026-10-11)

The previous bounded trial `20261011T042535421980Z-b1d2be84af5c4499a6f3df3e00b28bda` closed and verified all source saves/configuration unchanged. The user then selected fixed executable and test-state paths. `Launcher.prepare` now accepts an optional runtime parent; the local test uses `local/runtime/ppsspp-v1.20.4/app/PPSSPPWindows64.exe` and its `memstick/PSP/PPSSPP_STATE/ULJS00460_1.01_1.ppst`. Fresh save/configuration snapshots remain separate. On subsequent trials, the complete previous owned runtime is uniquely archived and current test saves seed the rebuilt fixed path. Unknown files and mismatched sources fail closed. PPSSPP-generated auxiliary folders are allowed for archival; cheats/plugins remain disabled in the rebuilt trial.

The final synthetic suite passed 189 tests, Ruff and strict mypy passed, and independent review found no remaining Critical/Important issues. Its relative-path Minor was fixed and reviewed. Postrun bundle/ISO rehashing remains a Minor hardening opportunity; they are verified before launch, while postrun checks cover original save/configuration sources and preserved snapshots/archives.

Fresh verified trial `20261011T043528563079Z-dd469bb2850d4aa79c71b79941c08c0a` successfully launched owned PID 8580 at the fixed path, with the expected game/window title and inherited Direct3D11 configuration. Windows Security Alert appeared for this new path. The user was asked to handle it; the agent did not operate the security prompt. The built-in screenshot command has not been exercised in this trial while the alert blocks the workspace. Fixed-path launch success does not establish reliable capture or autonomous play.

The five-minute trial closed its owned emulator successfully. Original saves, immutable source configuration and preserved snapshots verified unchanged. No battle inputs, save commands or screenshot menu action were sent. The fixed runtime remains in place for the next freshly backed-up trial; Windows approval and successful capture are still pending.

### Built-in screenshot retry succeeded (2026-10-11)

User-authorized retry `20261011T045146521633Z-fe627ab2ca1a435daa5afa560c726711` created fresh complete verified backups and preserved the previous fixed runtime in a unique archive. PPSSPP launched as owned PID 12548 from the same fixed executable path; the window inventory showed no Windows Security Alert this time.

Accessibility-only menu observation worked. Indexed clicks failed with `coordinate input geometry is unavailable`; keyboard navigation through the observed Debug menu (`Alt+d`, then `t` for Take screenshot) succeeded. Two newly created JPEG files were visually inspected: `ULJS00460_00000.jpg` (89,586 bytes, 14:55:34 Brisbane) and `ULJS00460_00001.jpg` (89,582 bytes, 14:55:57). Both show a complete nonblank battle map with terrain/grid/units; they have different SHA-256 hashes. Copies are preserved under the trial's ignored `evidence` directory. This proves repeatable built-in file capture for this configuration, not general Windows screen capture or confirmed cursor displacement. No battle inputs or save-state commands were sent. The observation gate still needs reliable automated capture integration and recognition before autonomous play.

The owned PPSSPP window closed via Alt+F4 after capture. The trial helper then completed successfully and verified original saves, immutable source configuration, snapshots and the preserved prior runtime archive unchanged. Screenshot SHA-256 values are `3fb93e7da210244a4f24696d3a1ce6da13f02f3202a8cbb64d7ed643761f85de` and `559b362d77ce5d7cb7fa4cd1045909e637625c1bc646667638840ce4b517b1bf` respectively. No code was committed.

### Protected screenshot collector implemented and live-validated

`capture.py` now binds collection to an owned `LaunchSession`, records baseline files before the async trigger, serializes requests, and accepts exactly one new correctly named JPEG/PNG after stable reads and full Pillow decoding. The observed test output size is 944 × 541. Frames contain immutable encoded bytes, digest, sequence and game/trial identity. Uniform blank images, wrong dimensions, ambiguous/overwritten files, unsafe links and revoked process binding fail closed. Timeout/cancellation/trigger failure disables reuse so late output cannot satisfy a later request. Identical bytes in separately created files remain valid when the game is stationary.

TDD observed missing-module failures and behavioral failures for unstable new-file reads and expired deadlines invoking the trigger. Independent review identified the synchronous-inspection deadline issue; explicit monotonic checks fixed it and re-review cleared blocking findings. The final unit suite passed 206 tests; Ruff, strict mypy and CLI help passed. An image-format rejection test's unrealistic 200 ms encoding budget was stabilized without relaxing dedicated deadline tests. No production menu recognition or autonomous CLI action was enabled.

Fresh protected trial `20261011T113500032086Z-69ae03ccbec848d1b267e2eb3c7b988f` launched owned PID 17204, with no repeated firewall alert. The supported Sky keyboard menu trigger supplied two capture requests; the collector returned sequences 1 and 2, each fully decoded as 944 × 541 and visually inspected as a clear game map. Evidence under the ignored trial directory contains `validated-frame-1.jpg`, `validated-frame-2.jpg` and the frame metadata JSON. Digests are `225f9dfbbbff4e77ceb657c3cd789c8712b900d1fcfd286875e55150dd0b05a3` and `86806f426b03b2a04aae4d227847d6d6c073ed59e65a16796c690bd95f35a151`. The helper closed its owned emulator promptly and verified original saves, immutable source configuration, snapshots and prior runtime archive unchanged.

This validates file collection through the supported conversational UI trigger. An unattended native menu bridge and full game-state recognition remain unimplemented. The next separately backed-up trial checks one short cursor input with visible displacement and release, rather than treating debugger acknowledgement alone as game success.

### Bounded cursor input outcome verified

Fresh verified trial `20261011T113946783806Z-12e36a08c9d748578676cc177a1afd73` launched owned PID 13416 from the fixed runtime, loaded the same selected state and verified debugger game/version identity. Initial CPU status was `(False, False)` (running). After the first validated screenshot, the adapter sent exactly `input.buttons.press` with button `right` and duration 2 frames, then completed its acknowledged release cleanup. Post-input CPU status remained `(False, False)`; no pause transition was introduced.

The two fully decoded 944 × 541 frames were visually compared. The white map cursor moved one grid cell to the right while the map remained visible. This establishes the bounded cursor outcome for this map/configuration, not all game menu actions or a production cursor decoder. Evidence includes `validated-frame-1.jpg`, `validated-frame-2.jpg`, frame metadata and `cursor-input.json`. Frame digests are `74b701c2edd8406d29a943ba83ed31dbf036a0300252258525e3697bc56859d5` and `ebfe8ff42f8a2f3951b334632734f615ebcf1e931043586749e967322c350876`. The helper closed PPSSPP and verified original saves, immutable source configuration, complete snapshots and preserved prior runtime archive unchanged. No unit action, combat or save command was sent.

Handover at the user's quota cap: five-hour usage was 26%, weekly 20%. Stop further implementation for this run after documenting these results. Resume with bounded recognition/profile discovery, retaining fresh backups before every new emulator trial. No commits or unattended battle execution are authorized by this handover.

### Unit information and maximum-resource corroboration

After the user authorized further work beyond the earlier quota cap, read-only analysis of the private 24 MiB RAM snapshot found a candidate sparse unit/form table with 0x50-byte blocks. Gundam 00's candidate block starts at `0x08E93A60`, Shenlong's at `0x08E92340`; their +0x12 words are 217 and 143 and imply origin `0x08E8F690`. This is not a deployed roster: numerous empty/variant records exist, and unit affiliation/positions/action flags are not established. Current/max HP offsets are +0x1C/+0x18, current/max EN +0x22/+0x20, defense/mobility/accuracy +0x0A/+0x08/+0x06. Do not infer active roster membership from plausible stats alone.

The first freshly backed-up startup (`20261011T121953161269Z-0aef4d8295754599a67cf13e7ca52e29`) failed its process identity check before any debugger connection or input. No PPSSPP process or application-error event remained. A second fresh backup and diagnostic retry (`20261011T122349407119Z-94a95f7edddb49f88cc791eaf5499f09`) started successfully as owned PID 15768; the isolated startup failure's root cause is unresolved and no production identity check was weakened.

The successful trial captured six screens and matching read-only record samples, briefly pausing only for memory reads and resuming in cleanup. The observed command menu contained Move, Attack, Spirit and Info. One bounded up input wrapped Move to Info; a new screenshot confirmed Info highlighted before confirmation. The information tabs were observed using bounded right inputs, without issuing unit movement, attacks, spirits or save commands.

| Evidence | Corroborated visible data |
| --- | --- |
| `screen-3.jpg`, Unit | Gundam 00 / Setsuna; HP 5000, EN 121, DEF 1150, MOB 165, HIT 170, LV 36, SP 55, will 150 |
| `screen-4.jpg`, Pilot | Setsuna F. Seiei; SP 55/95, will 150, LV 36, pilot combat stats 183/174/123/202/242/246, displayed spirit costs Focus 15, Sense 20, Yell 35 |
| `screen-5.jpg`, Mech | Gundam 00; HP **5000/5000**, EN **121/210**, DEF 1150, MOB 165, HIT 170 |

The user explicitly confirmed the current/maximum HP interpretation of 5000/5000. Fresh `records-5-08E90000.bin` bytes corroborate both Gundam 00 HP fields and both EN fields, along with defense/mobility/accuracy. This provides maximum-resource evidence for this named unit and tested state; Shenlong maximum HP 5300 still lacks fresh visible corroboration. Pilot current SP at `0x08EAA07C`, will at `0x08EAA07E` and level byte at `0x08EAA086` are promising old-snapshot candidates, not fresh live-correlated bindings; they were not included in this trial's memory sample and must remain unavailable operationally.

All six private images and record samples are under the successful trial's `evidence` directory with a metadata JSON. The helper closed PPSSPP and verified original save roots, immutable source configuration, complete snapshots and archived prior runtime unchanged. No unit action or combat occurred.
# Bounded reader checkpoint, 2026-10-11

The inspection-only decoder was exercised offline against `records-5-08E90000.bin` from protected trial `20261011T122349407119Z-94a95f7edddb49f88cc791eaf5499f09`, selecting the 0x50-byte record at 0x08E93A60. Record SHA-256: `b7d938eca4ad3b0934f6900b0979d4ac30ec82d1ed586634a77d4dbf1806341b`.

Decoded HP 5000/5000, EN 121/210, defense 1150, mobility 165 and accuracy 170 match the preserved mech-info screen. The user explicitly confirmed the HP numerator is current HP and denominator is maximum HP. Private `inspection-result.json` records the result and unavailable tactical fields. This is one corroborated unit record, not a deployed-roster or autonomous-battle validation. All 234 offline tests, Ruff and strict mypy passed; no emulator or save was changed by this offline check.
