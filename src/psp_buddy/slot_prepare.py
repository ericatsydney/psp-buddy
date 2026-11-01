"""M15 P1: a trial checkpoint from one of the user's save-state slots.

Pure logic, no emulator or file access. `local/m15-tools/prepare.py` copies and hashes the slot,
reads the state offline and passes the units here. The anchor ally is the unit the protected helper
checks at startup; it is chosen by a fixed rule so any save works without a hand-written manifest.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from psp_buddy import retry

PLAYER_GROUP = 0            # raw_menu_group_byte of the player's own units (NPC allies are 1)
FIXTURE_KEYS = ("object", "mech_id", "pilot_id", "hp", "en", "sp")


class PrepareRefused(ValueError):
    """A save that cannot become a trial checkpoint; `reason` names why."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _identity(u: Mapping[str, Any]) -> tuple[int, int, int] | None:
    values = tuple(u.get(k) for k in ("object", "mech_id", "pilot_id"))
    return values if all(type(v) is int for v in values) else None  # type: ignore[return-value]


def choose_anchor(units: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    """The living player ally with the lowest object whose (object, mech, pilot) is unique."""
    counts = Counter(_identity(u) for u in units)
    usable = [u for u in units
              if u.get("raw_menu_group_byte") == PLAYER_GROUP and type(u.get("hp")) is int
              and u["hp"] > 0 and _identity(u) is not None and counts[_identity(u)] == 1
              and all(type(u.get(k)) is int for k in FIXTURE_KEYS)]
    if not usable:
        raise PrepareRefused("no_anchor_ally")
    return min(usable, key=lambda u: u["object"])


def manifest(state: Mapping[str, Any], *, file: str, sha256: str, source: str, at: str,
             opening: Mapping[str, Any]) -> dict[str, Any]:
    """A checkpoint manifest in the M12-M14 format, plus the opening screen and its origin."""
    anchor = choose_anchor(state.get("units") or [])
    return {"file": file, "sha256": sha256, "source": source, "at": at,
            "fixture": {k: anchor[k] for k in FIXTURE_KEYS},
            "fixture_source": f"object {anchor['object']}: lowest-object living player ally, "
                              "read offline from the slot copy (m15 prepare)",
            "retry": retry.snapshot(state, sha256),
            "opening": dict(opening),
            "prepared_by": "m15 prepare"}
