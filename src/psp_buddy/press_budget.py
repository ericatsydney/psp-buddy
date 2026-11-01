"""M15 P3: will the next action's cursor walks fit in what is left of the per-turn budget?

Pure logic. The cursor walks one tap per tile (`info_navigation._goto`, long holds are off), so a
walk costs its Manhattan length plus corrections. One planned action walks: cursor -> unit (the
move-range read in `plan_act`), unit -> destination, destination -> target, and up to two map-proof
walks of one tile out and back (`act._cursor_walks`). The destination and target are known only
after the range read, so the turn checks twice: `reach_unit` before walking to the unit and
`act_cost` before the move walk. When either does not fit, the turn hands over (`cursor_budget`)
on the map instead of running out mid-action (m14s33n stopped at "cursor did not reach the unit").
"""

from collections.abc import Sequence

Tile = tuple[int, int]

PROOF_PRESSES = 2           # one map-proof walk: one tile out, one back
# Two map-proof walks plus one re-walk after a late cursor drift (act.move, CURSOR_CHECKS).
ACTION_MARGIN = 2 * PROOF_PRESSES + 2


def walk(path: Sequence[Tile]) -> int:
    """Taps to walk the cursor along the tiles in order."""
    return sum(abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(path, path[1:], strict=False))


def reach_unit(cursor: Tile, unit: Tile) -> int:
    """Presses to reach the unit, keeping one map proof in reserve so a turn never stops with
    the cursor on a unit it cannot leave."""
    return walk([cursor, unit]) + PROOF_PRESSES


def act_cost(unit: Tile, *, destination: Tile | None, target: Tile | None,
             spirit: bool = False) -> int:
    """Presses for a planned action from the unit's tile (cursor already there)."""
    path = [unit] + [t for t in (destination, target) if t is not None]
    return walk(path) + ACTION_MARGIN + (PROOF_PRESSES if spirit else 0)


def fits(cost: int, *, used: int, budget: int) -> bool:
    return used + cost <= budget
