# Original code reads for exact JIT-safe fingerprints

Evidence-bound debugger fix under approved session diagnostic testing. No game-input,
save, reconnect or failure bypass. Existing disabled trial remains untouched.

Use PPSSPPv1.20.4 documented memory.read replacements=false to obtain original
instructions for code fingerprints. Alternatives of masking JIT-looking words or dropping
anchors would fail to validate the original code and are rejected. Ordinary data reads
remain replacements=true. Original-code view temporarily normalizes native JIT/replacement
state inside PPSSPP and restores it via the pinned source's scoped destructor; no direct
memory-write request is allowed. Live correctness/restoration still needs protected testing.

Add DebuggerAdapter.read_original_code(address,size)->bytes. Require same asyncio task
owns observation_pause, operation lock held, known paused state and bound process identity;
PSP user RAM08800000..0A000000,4-bytealignedaddress/size,size4..4096. Revalidate ownership
at I/O dispatch. Normal request('memory.read',replacements=false) stays rejected, including
inside a pause; only the dedicated method authorizes this exact mode. Invalid input causes
no transport traffic; network/length/error uncertainty retains existing failclosed behavior.
No auto pause/resume/reconnect in the method; context owns pause cleanup. Decode exact
base64/length using existing semantics. Add meaningful RED tests before code.

Then adapt private collector code anchors to this method; static text/data anchors retain
ordinary data reads. Preserve byte/span budgets, exact comparisons and forensic evidence.
Fake retained snapshots must model raw JIT words versus canonical originals, rejecting
true original mismatch. All existing source/data hashes and live capability flags unchanged.
Run focused debugger/helper suites,Ruff,strictsource mypy,independent review,fullsuite before
any new protected trial. Keep current windowopen and noStart; newtrialrequiresfreshverified
backups and human steps under existing session approval. No commit/push.
