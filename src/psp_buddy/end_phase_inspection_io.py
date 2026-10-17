"""Strict version-one nested descriptor for offline End Phase inspection."""

from .end_phase_inspection import EndPhaseInspectionProfile
from .inspection_io import _integer, _keys, _object, _text
from .menu_membership_inspection_io import parse_menu_membership_inspection_profile
from .unit_pool_inspection import CodeAnchor
from .unit_pool_inspection_io import _list


def parse_end_phase_inspection_profile(values: object) -> EndPhaseInspectionProfile:
    """Accept exactly the supported recipe and inherit nested identity."""
    values = _object(values)
    _keys(
        values,
        {"kind", "schema_version", "menu_membership_profile", "code_anchors", "evidence_ids"},
    )
    if values["kind"] != "end_phase_inspection" or _integer(values["schema_version"]) != 1:
        raise ValueError("Unsupported End Phase inspection kind or schema version")
    anchors = []
    for item in _list(values["code_anchors"], 1, 16):
        anchor = _object(item)
        _keys(anchor, {"address", "size", "sha256"})
        anchors.append(
            CodeAnchor(
                _integer(anchor["address"]), _integer(anchor["size"]), _text(anchor["sha256"])
            )
        )
    return EndPhaseInspectionProfile(
        parse_menu_membership_inspection_profile(values["menu_membership_profile"]),
        tuple(anchors),
        tuple(_text(item) for item in _list(values["evidence_ids"], 1, 32)),
    )
