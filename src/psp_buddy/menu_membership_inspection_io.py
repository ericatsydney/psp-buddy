"""Strict version-one nested descriptor for offline menu membership."""

from .inspection_io import _integer, _keys, _object, _text
from .menu_membership_inspection import MenuMembershipInspectionProfile
from .positioned_inspection_io import parse_positioned_inspection_profile
from .unit_pool_inspection import CodeAnchor
from .unit_pool_inspection_io import _list


def parse_menu_membership_inspection_profile(values: object) -> MenuMembershipInspectionProfile:
    """Parse exact keys without inferring menu labels from counts or group bytes."""
    values = _object(values)
    _keys(
        values,
        {
            "kind",
            "schema_version",
            "positioned_profile",
            "menu_mask_table_address",
            "expected_category_masks",
            "ally_category_index",
            "foe_category_index",
            "code_anchors",
            "evidence_ids",
        },
    )
    if values["kind"] != "menu_membership_inspection" or _integer(values["schema_version"]) != 1:
        raise ValueError("Unsupported menu membership kind or schema version")
    anchors = []
    for item in _list(values["code_anchors"], 1, 16):
        anchor = _object(item)
        _keys(anchor, {"address", "size", "sha256"})
        anchors.append(
            CodeAnchor(
                _integer(anchor["address"]), _integer(anchor["size"]), _text(anchor["sha256"])
            )
        )
    return MenuMembershipInspectionProfile(
        parse_positioned_inspection_profile(values["positioned_profile"]),
        _integer(values["menu_mask_table_address"]),
        tuple(_integer(mask) for mask in _list(values["expected_category_masks"], 4, 4)),
        _integer(values["ally_category_index"]),
        _integer(values["foe_category_index"]),
        tuple(anchors),
        tuple(_text(item) for item in _list(values["evidence_ids"], 1, 32)),
    )
