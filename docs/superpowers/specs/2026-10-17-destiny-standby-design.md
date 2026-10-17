# Destiny Move/Standby diagnostic design

Extension of the human-controlled testing approved in this conversation: the user
proposed Move one tile down then Standby and approved the staged procedure by
reporting preview ready. Existing all-session testing approval remains valid.
No additional production action capability is introduced; Standby is diagnostic only.

Use a separate private helper entry point with fresh original/portable full saves
and configuration SHA-256 backups through the existing Launcher. Do not attach,
hot-patch or replay the running helper, force-close PPSSPP, or reload the open game.
Fresh launch requires the user to close the existing window normally first.
Alternatives: patching the running helper would invalidate reviewed runtime code;
continuing the original attack state machine would mislabel evidence. A dedicated
fresh diagnostic sequence is bounded and avoids replaying Z combat.

Stages: baseline -> unit-baseline -> move-preview -> post-move -> post-standby.
Bind the unique living raw-group0 unit by current Info plus expected mech/pilot/HP/EN;
for this fixture Destiny is mech197,pilot208,HP5200,EN230,object149303288.
Preview destination must be exactly starting tile+(0,1), in bounds, and memory
must still show starting tile/resources. Post-move requires human confirmation and
actual destination tile; HP/SP/maxima unchanged, only chosen EN may decrease.
Post-Standby requires explicit human acknowledgement and same tile/resources as
post-move. Candidate flags/counters may change and are recorded, never interpreted
as can_act. All stages preserve roster identities, affiliation, other units' resources
and positions, all allies alive. Two stable observations and existing exact canonical
fingerprints, byte budgets, ownership, identity and failure-disable rules apply.
No automatic input, combat, save, EndTurn, recovery, close, reconnect or cheat.
Current code/flags are research evidence only. Original capture spans contain raw
object status bytes; comparisons must retain their exact source and offsets.

Acceptance: tests prove ordered stages, current Info binding, strict schema and
fresh acknowledgements, exact one-tile destination, real preview vs moved memory,
chosen-only EN loss, unchanged nonchosen units, no combat/extra roster changes,
explicit post-Standby and failure latching. Existing helpers regressions pass.
Independent code review before any new live trial. No commits.


Candidate-byte evidence must be explicitly stable in both captures: chosen object
+8,+0x25,+0x60, from replacements=true spans. Reject missing, malformed or conflicting
coverage. Existing representative stable_signature alone does not contain these raw
bytes. Export offsets/values as diagnostic candidates only, with no can_act claim.
