# End Phase count linkage — 17 October 2026

## Result and limits

Offline code tracing now connects the existing two-bit object counter to the number
formatted beside the game's **Unmoved Units** label in its End Phase confirmation.
This advances the earlier screenshot/count correlation to a defining UI call path.
It does not establish movement range, legal attacks, turn ownership, a complete phase
state machine, or permission to execute a battle action. No production reader or live
emulator operation was added. Transform remains excluded from the MVP.

## Defining UI path

Function `0x08878B94` calls aggregate `0x0888449C` at `0x08878BA8` and retains its result.
For a positive count, it builds decimal digits from the glyph table at `0x08B4C928`,
then concatenates the prefix at `0x08B4C940`, the digit buffer, and the suffix at
`0x08B4C95C`. The second prompt string is taken from `0x08B4C96C`.
These strings are CP932 fullwidth characters. NFKC normalization yields:

| Address | Normalized text |
| --- | --- |
| `0x08B4C928` | `0123456789` |
| `0x08B4C940` | `UnmovedUnits:` |
| `0x08B4C95C` | `unit/s` |
| `0x08B4C96C` | `End phase?` |
| `0x08B4C988` | `End phase.` |
| `0x08B4C9A0` | `Proceed?` |

The zero branch uses the last two strings instead. Counts of 100 or more are reduced
modulo 100 before formatting; a future inspection report should retain the raw count
and distinguish the displayed count. The prompt is opened through the existing UI
manager, type `0x24`, and callback `0x08878D28` invokes `0x0882FB30`. No callback was run.

The previous exact-ASCII search found none of these labels because this retained image
stores them as fullwidth CP932. That bounded negative remains correct; it was not evidence
that the labels were absent in every encoding.

## Aggregate and null behavior

The aggregate queries the representative cache with mask `1`, iterates matching actors,
and increments its total when helper `0x08884AC4` returns false. The mask predicate uses
object byte `+0x15` through the established variable-shift filter. It is narrower than
Ally-menu mask `0x000F`; the two scopes must not be substituted.

The helper returns true only when its actor resolves to a nonnull object and
`(u8(object+8) >> 3) & 3` equals zero. Its object-resolution path includes representative
lookup, so the aggregate is precisely a count of the inverse helper result, rather than
an unconditional direct-object positive-counter formula. A null resolution also produces
false. Any future trusted inspection interface must reject unresolved rows instead of
presenting them as proven actionable units.

The two-bit counter's increment, decrement and initialization paths were established in
[the earlier counter research](2026-10-16-counter-and-tile-cache-limits.md). A positive
counter is now connected to this particular UI prompt. This does not prove every positive
unit has a legal Move or Attack command, or identify exactly which action consumes it.

## Reproduction and next dependency

Private verifier `local/action-ui-count-20261017/verify.py` asserts key UI instructions,
decodes and checks all six strings, and compares three complete code/data windows between
the original and portable retained clean RAM. Every window matches exactly. Source hashes,
window hashes and exact string bytes are retained in its ignored findings JSON; disassembly
is retained separately. No game bytes or private profiles are added to tracked documents.

Independent verifier `local/action-count-link-20261017/verify.py` compares nine defining
code windows between both clean states and checks the related-actor resolver's initial
record search for every retained cache row. None has a matching enabled relationship
record, proving fallback to the original actor object for these inputs. It reproduces:

| Retained map | Cached actors | Mask1 actors | Positive / zero counters |
| --- | ---: | ---: | ---: |
| Original | 69 | 24 | 13 / 11 |
| Portable | 12 | 8 | 5 / 3 |
| Current | 26 | 20 | 20 / 0 |

This counts actors with a positive counter, rather than summing counter values; counter2
would contribute one actor. Independent review confirms the count-to-prompt formatting
path and the null-resolution/display-modulo caveats, with no blocking finding.

Next: prepare a bounded offline inspection design for written review. The interface
must describe the observed counter and End Phase count scope, retain null/related-actor
resolution gates, and avoid an unproven general `action_available` promise. Live action-transition trials and battle actions remain behind
the existing save-protection and approval gates. Do not repeat form, position or menu work.

## Approved offline reader implementation

The user approved the written design and the end_phase_inspection descriptor is implemented.
It composes validated menu/position/stat records, rejects unsupported resolver cases via
the representative source/cache exclusion invariant, and reports counter0..3 and both raw
and displayed counts. Eight actual offline CLI fixtures reproduce original13,portable5
and current20 while preserving all old rows. No general action_available field or live
capability is enabled. Fullsuite1078passed,1existingprivilege skip; lint/types/build pass.
Next: bounded causal action-transition evidence and phase/command legality, with written
trial review and fresh verified backups before any future emulator operation.
