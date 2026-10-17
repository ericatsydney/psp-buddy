# Offline comparison with other-map saved states

## Result

The code-defined224-slot object table was checked against two existing slot1 saved states
whose thumbnails show different ground maps from the space-map development fixture.
No emulator launch, load, save, input or original-file modification was required.
The sources were already-complete verified snapshots, with state and thumbnail SHA-256
matched to the retained manifest before accepting extraction.

| Saved-state source | Candidate records | Raw stateword groups |
| --- | ---: | --- |
| Original-memory-stick slot1 snapshot | 69 | 24 at0x1,25 at0xC01,20 at0x401 |
| Portable-memory-stick slot1 snapshot | 12 | 8 at0x1,4 at0xC01 |
| Space-map development fixture | 26 | 20 at0x1,5 at0xC01,1 at0x401 |

All three have identical retained accessor code for base08E61F50, stride104 and capacity224.
The candidate condition remains byte0 nonzero and word+0x14 bit0 set. Counts vary by state;
no fixed robot count, faction count or stack-list address is necessary for this comparison.
Raw statewords are reported here as observations, not a universal affiliation definition.

## Position corroboration

Two independent visual reviews counted12 unit sprites in the portable slot1 thumbnail and
matched all12 extracted coordinate pairs to occupied grid cells. The white square is a
cursor and was excluded. A fitted40-pixel grid translation maps the candidate world tiles
to this screenshot; no subpixel or one-pixel sprite-centre measurement is claimed.
This supports relative position meaning across a different map, but does not establish
absolute map origin, dimensions, off-screen completeness, terrain or legal actions.
Private details: `local/state-memory-20261016/visual-corroboration.json`.

## Extraction method and provenance

Private research helper: `local/state-memory-20261016/extract.py`.
Reproduce with `.venv/Scripts/python.exe local/state-memory-20261016/extract.py`.
It supports only revision5, compression1 states with the specifically checked Memory v3
layout/model/32MiB RAM size. Unsupported layouts fail closed. It reads bounded state data,
checks Snappy output length, serialization section and RAM-end cookies, extracts24MiB
of user RAM at08800000, and checks state hashes again after reading. Inputs remain unchanged.
Synthetic checks cover literals, extended lengths, three copy forms, overlapping copies,
truncation, invalid offsets, bad preambles and trailing bytes. These are research checks,
not a shipped file-format parser or complete serialized-state validator.

The saved states record creator v1.9.3. The following v1.20.4 sources document the compatible
header/reader and Memory section format; they are not the files' originating-version evidence:
[PPSSPP serializer header](https://github.com/hrydgard/ppsspp/blob/v1.20.4/Common/Serialize/Serializer.h),
[serializer implementation](https://github.com/hrydgard/ppsspp/blob/v1.20.4/Common/Serialize/Serializer.cpp),
[Memory serialization](https://github.com/hrydgard/ppsspp/blob/v1.20.4/Core/MemMap.cpp).
The bounded decoder follows the [Snappy raw format](https://github.com/google/snappy/blob/main/format_description.txt).
Official sources establish encoding, not game-specific roster semantics.

Evidence sources under protected trial20261015T120025749948Z-0289b926396c4c3683c13be0b1f44c51:
`snapshot/1-PPSSPP_STATE/ULJS00460_1.01_0.ppst` and
`snapshot/3-PPSSPP_STATE/ULJS00460_1.01_0.ppst`, plus corresponding thumbnails and manifest.
Raw extracted RAM and hashes remain ignored under local/state-memory-20261016.
Independent review found no Critical/Important issue in the scoped helper; manifest
binding was then made explicit in the helper and reverified, and truncated headers reject.

## Remaining gates

This advances cross-state structural and visible-position evidence. It does not complete
another-stage tactical acceptance: stage IDs, all affiliation meanings, current-form and
primary-pilot selection, complete membership, dimensions and action state remain unresolved.
The older ground-map thumbnail is at an End phase confirmation prompt; no confirmation or
other input was issued, and no future trial may auto-confirm it.
No production code, tactical profile, CLI enablement, commit or publication was made.
The earlier request for an additional state is optional now that existing candidate states
have been found; do not repeatedly ask the user for the same material.
