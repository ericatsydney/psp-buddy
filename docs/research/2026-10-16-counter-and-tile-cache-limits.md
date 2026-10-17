# Counter and tile-cache limits — 16 October 2026

## Two-bit counter candidate, not a boolean action flag

A code-backed counter occupies bits3..4 of unit object byte+8:
`counter = (byte >> 3) & 3`. Increment, positive-guarded decrement, initialization and zero
consumers are defined in the retained instructions. Initialization can set1 or2; the2 path
uses a positive pilot-entry query for ID27. No ability name is assigned from the numeric ID.
An actor-specific path initializes from another function, and a mode field is extracted from
bits4..5 of08E08B8B. These are structural facts, not a complete gameplay action definition.

The original map's raw-state1 group has13positive and11zero counters, matching the visible
End Phase prompt's UnmovedUnits13. Portable raw-state1 has5positive/3zero; development raw-state1
has20positive. The actual UI count writer and causal action transition remain unverified.
Therefore action_available remains unknown in the new geometry reports.

Do not use bit3 alone: counter2 is positive but has bit3 clear. Do not use word+8 bit11 as
universal spent/complement state: it is set through a separate writer and does not generally
track the counter. Do not use object+0x22; that separate counter is unlabelled and zero for
all24original raw-state1 records. A tested real list predicate0884D2CC accepts all24 rather
than13, so it is not the requested unmoved test. Two mask1 query leads resolve to boolean/list
operations, not the count aggregator. Raw English text searches were negative, which does not
exclude other encodings, packed strings or texture text.

Reproducer, exact source hashes, code windows and all candidate distributions:
local/action-availability-20261016/verify.py, findings.json and findings.md.

## Derived tile classifications can be stale

Cell byte+9 is built by08911CF8 from base cell flags and cell+0x0A, then overwritten using
actor cells and a context actor. Base classes0/1/3 and overlay classes2/4 are derived values.
Getter consumers perform categorical tests. No static terrain-ID or movement-cost meaning
has been established.

The portable state is a concrete counterexample to universal occupancy decoding:

- Three current candidate objects occupy class1/3 cells, not2/4.
- Six class2/4 cells are outside current candidate positions, including three empty pool slots
  with old C00 state and three positions without a current pool-slot match.
- The retained context actor exists as an actor row but currently has no object pointer.

The current development map happens to put all26candidate objects on classes2/4; the original
map has every byte+9 zero. A current-map positive fit would therefore miss stale/conditional
state in the other maps. Do not feed these classifications into tactical legality or claim
that they enumerate deployment. The direct object coordinates are separately validated;
the candidate position sets have no duplicate cells in the three retained maps.

Nine defining windows match both clean states. Reproduction and exact exceptional cells:
local/tile-property-paths-20261016/verify.py, findings.json, findings.txt and code.txt.

## Inspection efficiency accounting

Offline accounting for known candidate pool/catalogue, dimensions, selected representative
descriptors and basic-stat windows gives the following possible merged spans:

| Candidate objects | Exact required bytes | Candidate merged reads | Candidate merged bytes |
| ---: | ---: | ---: | ---: |
| 69 | 52,464 | 19 | 113,756 |
| 12 | 42,204 | 14 | 61,328 |
| 26 | 44,724 | 17 | 102,140 |

This uses at most4KiB gaps per merge and64KiB per window. Pointer-discovery roots, source/cache
consistency lists and tables, screenshots, identity/protocol overhead and latency are excluded.
The comparison is with a24MiB full retained RAM sample. It is a byte/read-window estimate,
not an implemented collector, live benchmark or speed guarantee. The old screenshot-handoff
helper still collects full RAM; a new bounded helper must follow the approved trial design
and its yet-to-be-approved execution plan.

Reproducer: local/read-span-budget-20261016/verify.py and findings.json. No emulator actions,
production changes or commits were involved in this accounting.
