# M15 Task 1 — screen signatures from retained RAM dumps (in progress)

Question: which memory fields tell `map`, `move_range`, `unit_commands`, `post_move_menu`, `weapon_list` and
`target_select` apart? Offline only; no emulator ran.

## Evidence set

`local/m15-screens/labels.json`: 33 retained 24 MiB dumps (0x08800000), labelled from the trial logs:
`local/move-attack-trial-20261017/m1_inventory.py` (18-19 Oct), the m14rec3 mailbox order (31 Oct), the
m14s33a cursor recon (26 Oct, map after back-out), m9livesp3 (spirit list / map) and m11menu1 (Command menu rows).
Five dumps are still `unchecked` (m12alert1, m9livesp1). Scripts: `local/m15-screens/diff.py` (window scan),
`scan.py` (whole-RAM scan for words that change at every in-run transition and are constant per label).

| Screen | Stage 23 dumps | Stage 33 dumps |
| --- | --- | --- |
| map | wrec 01, m9livesp3 02 | m14s33a 01-03 |
| unit_commands | m11menu1 01-05 | m14rec3 01-02 |
| move_range | mv 01 | — |
| weapon_list | wrec 02/04/06, zrec 01/05 | — |
| target_select | wrec 07/08/10 | — |
| post_move_menu | — | m14rec3 03-06 |

## Findings (31 Oct)

- **0x08E4BB9C (u32) is the free count of a 32-node pool** (nodes 0xC bytes from about 0x08E4B9F8; free-list
  head 0x08E4BBAC). It drops by one per open UI layer. Stage 23: map 31, system menu / Command menu 30,
  weapon list / move range / spirit list 29, target select 28. Stage 33: map **30**, Command menu 30, post-move
  menu 28. So the count is relative to a **per-map baseline** (stage 33 holds one extra node on the bare map):
  it proves "one layer closed" after each Cross, but not which screen is open on an unknown save.
- Same-count screens are not separated by any word that is constant per label across runs: weapon list vs move
  range vs spirit list (29), target select vs post-move menu (28), Command menu vs system menu (30).
- Whole-RAM scan: 3156 words pass the per-label test, but all except 0x08E4BB9C are render/display-list data
  (0x08CE8xxx) or unit-table data that varies by run. Window flag words 0x08E4BDE4 / 0x08E4BF74 disagree across
  runs on the same screen (m9livesp3 map vs wrec map) and are rejected.
- The menu slots (0x08E4BE34 Command, 0x08E4BEB4 post-move, 0x80 apart) sit at +0x58 in 0x80-byte objects
  (0x08E4BDDC, 0x08E4BE5C, ...). Their counts persist after a menu closes (m14s33f), as known.

## Pool walk (31 Oct, second iteration) — screens identified

`local/m15-screens/pool.py`: nodes are 12 bytes `[slot, next, prev]` at 0x08E4B9F8 + 12k (32 nodes); each node's
slot word (0x08E4B96C + 4k) points at a window object; the free list starts at 0x08E4BBAC. In all 33 dumps the
walked free list length equals the count at 0x08E4BB9C. Allocated window objects (first word = type pointer,
the same on both stages); 0x08E4BD0C (type 0x08CDB3B0) is always allocated (root):

| Open objects besides the root | Screen | Evidence |
| --- | --- | --- |
| none | map, or the "range view" below | stage 23: wrec 01, m9livesp3 02, m12alert1 01-02 |
| 0x08E4CED4 (type 0x08CDAF34) only | map (stage 33, after the back-out) | m14s33a 01-03 |
| 0x08E4BDDC (0x08CDAE34) | Command menu **or** system menu (Cross closes either) | m11menu1 01-05, m14rec3 01-02, sys 01, end 01 |
| BDDC + 0x08E4BF6C (0x08CDAE14) | move range (after Move) | mv 01 (one dump) |
| BDDC + 0x08E4C5C4 (0x08CDAD14) | weapon list | wrec 02/04/06, zrec 01/05 |
| BDDC + C5C4 + 0x08E4C67C (0x08CDB390) | target select | wrec 07/08/10; **stage33-slot2 checkpoint** (offline) |
| BDDC + 0x08E4BE5C (0x08CDAE34) + BF6C | post-move menu | m14rec3 03-06 |
| BDDC + 0x08E4D208 (0x08CDB2D0) | spirit list | m9livesp3 01, m9livesp1 02-03 |

- The stage-33 checkpoint (`local/m15-screens/checkpoints.py`, offline Snappy unpack) opens on the target-select
  set, matching the recorded back-out (m14s33a: Cross, Cross, close_command_menu, Cross).
- **Gap — "range view"**: in m14s33a, three Crosses should have closed the three open windows, yet a fourth
  Cross was needed ("move range" in the notes; no dump was taken there, so the pool state is inferred, and the
  state-read refusals in that run came from the old fixed cursor address, not from this screen). After that
  Cross, 0x08E4CED4 appeared. Stage-23 map dumps never hold CED4, so its presence is not a map proof. No
  retained dump captures the range view itself.
- Save-state format: the user's PPSSPP_STATE slots 0-2 are revision 5 / Snappy (creator v1.9.3) and unpack;
  checkpoints written by the trial PPSSPP v1.20.4 (`turn7-*`) use compression 2 and are refused, as the spec
  requires for unsupported formats.

## The user's slots, read offline by `prepare.py` (31 Oct)

| Slot | Turn | Open windows besides the root | Classified |
| --- | --- | --- | --- |
| 2 (stage 33) | 5 | Command + weapon list + target select | `target_select` (3-Cross back-out) |
| 1 | 4 | post-move menu set (Command, 0x08E4BE5C, move range) + weapon list + target select + **0x08E4C81C** (type 0x08CDAD74) | `unknown` |
| 0 | 1 | Command (count 7, row 0: the system menu) + **0x08E4E174** (type 0x08CDAFF4) | `unknown` |

Slot 1 looks like an attack chosen after a move (target select over the post-move menu), with one more
window not seen in any retained dump; slot 0 looks like a system-menu sub-window at turn 1. Both refuse
before launch, as the user chose. Supporting them needs evidence of what Cross does there (Task 1b).

## Live check (m15s33b, 31 Oct) — the "range view" is the map

`run.py m15-s33`: the live `state.screen` read `target_select` as prepared; three Crosses, each re-read,
went target_select -> weapon_list -> unit_commands -> no_menu, and the cursor walk to the anchor tile
(11,18) succeeded. Screenshots ULJS00460_00003 (after the third Cross) and _00004 (after the walk) show the
plain map with a yellow range highlight around the unit under the cursor, which moves with the cursor to the
next unit. So the 26 Oct "move range" after `close_command_menu` was this hover highlight, not a screen; the
fourth Cross in m14s33a was not needed. `no_menu` + a working cursor walk is the map. The first plan_act
fired from there (GNMissile).

## Next step

Task 1 is done for every menu screen. Open: the range view vs the bare map (no pool object in either). Options
for Task 1b (protected recon, needs the user's go-ahead as the first live M15 trial): dump RAM in the range view
and on the map from the stage-33 checkpoint after 3 Crosses / 4 Crosses, and test whether a Cross on the bare
map is a no-op (then the back-out can always end with one checked extra Cross). Meanwhile Tasks 2 and 4 do not
depend on it.
