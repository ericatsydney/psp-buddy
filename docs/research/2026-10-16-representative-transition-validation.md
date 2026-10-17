# Representative selection: one reversible form change

The approved human-assisted trial corroborated Z Gundam -> Waverider -> Z Gundam
in the isolated slot-2 fixture. This validates one form-selection lifecycle, not
crew changes, stage changes, save/load recovery or autonomous battle readiness.

## Protection and observations

Trial `20261016T075445338602Z-e3804b5a17964b04b11a3126525f2f93` used the existing protected
launcher and owned Python debugger. Fresh complete backups of four original/portable
save/state roots contained 84 files; every copied file was SHA-256 verified. Both
configuration files were also backed up and verified. Immutable snapshots and the
previous runtime archive remain separate from the writable trial memory stick.

The user performed all navigation and both transformations and supplied fresh Unit-tab
screens. The assistant issued no game inputs or saves. Each stable phase used two
separate bounded paused observations with normal-running checks between them. Each
observation read 188,156 bytes, within the 1 MiB budget. Original/snapshot/archive
preservation checks passed after observations. The emulator remains open; no final
closure, discard or reload was performed.

Private evidence is in `local/transition-trial-20261016/run-20261016T175435/evidence`:
`observation-002.json` through `observation-004.json`, their raw captured spans and
fresh screens, plus `transition-acceptance.json`. No game bytes or images are public.

## Corroborated results

| Field | Initial Z Gundam | Waverider | Returned Z Gundam |
| --- | ---: | ---: | ---: |
| Mech ID | 122 | 123 | 122 |
| Pilot ID | 134 | 134 | 134 |
| Current HP | 4700 | 4700 | 4700 |
| Current EN | 128 | 128 | 128 |
| SP | 24 | 24 | 24 |
| MV candidate, record byte +0x05 | 6 | 8 | 6 |
| DEF, record u16 +0x0A | 1000 | 900 | 1000 |
| MOB, record u16 +0x08 | 115 | 125 | 115 |
| HIT, record u16 +0x06 | 145 | 145 | 145 |

The selected actor changed while its object address and pilot remained the same.
Selector-pair index 2 changed exactly `(122,134) -> (123,134) -> (122,134)`; the other
89 pairs were unchanged. The source actor list was unchanged. The cache replaced
only the chosen representative actor and restored it on return. All 26 candidate
objects had one representative in every stable observation. Every other representative
binding and all object tile coordinates on the 24x34 map remained unchanged.

The complete decoded stable signature on return equals the initial signature. This
comparison covers selected links/resources, candidate/source/cache/representative
relations, selector pairs and tile geometry; it does not claim every RAM byte is equal.

Both forms' stat records already contained their respective MV/DEF/MOB values before
and after the transformation. Selection switches between existing form records;
the observed values do not prove those stat bytes were rewritten by transforming.
Name text is not decoded: the IDs are linked to the user-visible form labels.

## Limits and next work

Pre-Info deferred-cache timing was intentionally not sampled: the private helper rejects
that optional diagnostic phase because stale Info globals cannot authenticate resources.
A clear dirty bit still does not prove coherence. MV byte +0x05 matches this pair, but
does not establish legal movement range, reachability or a universal movement contract.

Production representative selection remains unimplemented. The next dependent step is an
evidence-bound offline representative-inspection design and plan, reviewed before code.
Its contract should preserve unsupported/unknown results, reject incomplete coverage,
and keep all tactical/autonomous capability flags false. Further live trials or broader
state-lifecycle claims require their own applicable evidence and approval boundaries.
