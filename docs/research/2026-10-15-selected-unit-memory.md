# Selected Unit screen memory links

## Scope and evidence

Game ULJS00460 version 1.01, English v0.8, PPSSPP 1.20.4. Research only;
no production binding or automatic battle behavior is enabled.
Protected trial: `20261015T065827988941Z-c31825d738e445cc9db4e7fa0ceb0173`.
Private screenshots, RAM dumps, hashes and comparisons remain in its `user-evidence` folder.
Samples: Shenlong, Gundam 00, unchanged Gundam 00, Shenlong, Dancouga Nova.

## Selected records

Little-endian u32 chain for mech: `u32(u32(0x08E60674) + 4) + 0x10`.
Pilot: `u32(u32(0x08E60678) + 4) + 8`.
Duplicate selected globals at `0x08E60680` and `0x08E60684` corroborate both.
The return to Shenlong reproduced the same record pointers and HP/EN/SP.
Dancouga Nova was a held-out third robot: all 14 checked visible values matched,
including HP5782, EN9, SP44 and level33.

| Screen | Mech record | Pilot record | Mech/pilot descriptor indices |
| --- | --- | --- | --- |
| Shenlong/Wufei | 0x08E92340 | 0x08EA6270 | 143 / 150 |
| Gundam 00/Setsuna | 0x08E93A60 | 0x08EAA040 | 217 / 242 |
| Dancouga Nova/Aoi | 0x08E95040 | 0x08EADC0C | 287 / 331 |

Candidate mech descriptor table base `0x08E67C80`, stride12; pilot base
`0x08E6A3F8`, stride8. These bases are inferred from three observed rows.
Pilot level is a byte at record+0x46, not a u16. Pilot SP is u16+0x3C;
will is u16+0x3E. Combat fields at +0x1E through +0x28 match all three screens.

## Relationship lists

Arrays `0x09601B20..0x09601F40` and `0x096027F0..0x09602C10` (end exclusive)
each contain132 unique signed32 mech/pilot pairs. They are permutations of the same
pairs and remained byte-identical across all five samples. Container headers at
`0x09601330` and `0x09602000` contain the respective base and count0x84.
Dancouga/Aoi pair287/331 occurs at first-list row59 and second-list row37.
These observations support stable relationship lists, not proven deployment lists.

A separate16-byte descriptor-pair row at `0x091C04D0` associates Dancouga287
with Aoi331. The next three rows share mech287 with pilots332..334, consistent
with a multi-pilot robot. Their fourth words are pointers, not unit coordinates.
Never assume one pilot row equals one deployed robot.

## Next validation gates

1. Fresh backed-up restart/reload; reauthenticate and corroborate selected chains.
2. Repeat on a different stage; distinguish stable build tables from stage allocations.
3. Identify deployed membership, side and world coordinates against visible map units,
   including inactive/reserve negatives. Cursor coordinates alone are insufficient.
4. Only then add evidence-bound production decoding with meaningful failing tests,
   focused implementation, complete verification and independent review.

Current findings do not establish deployment count, side, map position, action status,
terrain or legal actions. Reload and cross-stage checks remain outstanding.


## Combined selected relationship and checkpoint

Globals `0x08E6067C` and `0x08E60688` track the selected16-byte relationship row:
Shenlong `0x091C0660`, Gundam00 `0x091C0310`, Aoi `0x091C04D0`.
Both follow the same A-B-B-A-third sequence as the separate descriptors. This directly
links the selected screen to the relationship rows, without proving deployment membership.
Private bounded analysis: `local/third-unit-relation-20261015/findings.json` and
`dynamic.json`. Region0x096E24xx contains references worth investigating, but its mixed
record shapes and packed words have no validated coordinate interpretation.

Reload was not performed: PPSSPP's unsaved-progress exit dialog is awaiting explicit user
confirmation. Current process remains open; no save, load or battle command was issued.
Latest quota checkpoint:11% five-hour allowance remaining. A new launch must start with
fresh complete verified backups after closure; do not reuse the previous trial receipt.
